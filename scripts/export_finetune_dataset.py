from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = REPO_ROOT / "tests"
RESULTS_ROOT = REPO_ROOT / "results"
EXAMPLES_ROOT = REPO_ROOT / "examples"
DEV_LOG_PATH = REPO_ROOT / "DEVELOPMENT_LOG.md"
DIAG_FIXTURE_ROOT = TESTS_ROOT / "fixtures" / "diagnosis_cases"
DATASET_NAME = "cae_cli_finetune_v2"
DATASET_HQ_NAME = f"{DATASET_NAME}_hq"
DEFAULT_OUTPUT = REPO_ROOT / "datasets" / "finetune" / "cae_cli_v2"
SYSTEM_PROMPT = (
    "You are a CAE diagnostic assistant. "
    "Return strict JSON only, no markdown, no extra keys."
)


@dataclass
class RawSample:
    sample_id: str
    task_type: str
    source_group: str
    source_ref: str
    user: str
    assistant: dict[str, Any]
    quality_score: float
    tags: list[str]


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except Exception:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clip_text(text: str, max_chars: int) -> str:
    normalized = _normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    head_budget = int(max_chars * 0.65)
    tail_budget = max_chars - head_budget - 24
    return (
        normalized[:head_budget].rstrip()
        + "\n\n...[truncated]...\n\n"
        + normalized[-tail_budget:].lstrip()
    )


def _extract_key_log_snippet(text: str, max_lines: int = 42) -> str:
    lines = _normalize_text(text).splitlines()
    if not lines:
        return ""
    keywords = (
        "error",
        "fatal",
        "warning",
        "residual",
        "converge",
        "courant",
        "iterations reached",
        "cannot find",
        "no such file",
        "undefined",
        "success",
        "completed",
        "not converged",
    )
    chosen: set[int] = set(range(min(8, len(lines))))
    chosen.update(range(max(0, len(lines) - 8), len(lines)))
    for idx, line in enumerate(lines):
        lowered = line.lower()
        if any(token in lowered for token in keywords):
            chosen.add(idx)
            if idx > 0:
                chosen.add(idx - 1)
            if idx + 1 < len(lines):
                chosen.add(idx + 1)
    ordered = sorted(chosen)
    kept: list[str] = []
    for idx in ordered[:max_lines]:
        kept.append(lines[idx])
    return _clip_text("\n".join(kept), 2800)


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _route_for_solver_status(status: str) -> str:
    mapping = {
        "failed": "runtime_remediation",
        "not_converged": "convergence_tuning",
        "success": "physics_diagnosis",
        "unknown": "evidence_expansion",
    }
    return mapping.get(status, "evidence_expansion")


def _next_action_for_route(route: str) -> str:
    mapping = {
        "runtime_remediation": "Inspect runtime setup before physics diagnosis.",
        "convergence_tuning": "Tune solver controls before interpretation.",
        "physics_diagnosis": "Proceed with physics interpretation and confidence checks.",
        "evidence_expansion": "Collect additional logs and metadata before deciding.",
    }
    return mapping.get(route, "Collect evidence before taking action.")


def _primary_issue_key(keys: list[str]) -> str:
    return keys[0] if keys else "unknown"


def _issue_route_hint(keys: list[str]) -> str:
    lowered = {item.lower() for item in keys}
    if "convergence" in lowered:
        return "convergence_tuning"
    if any(
        key in lowered
        for key in {"results", "syntax", "material", "boundary", "mesh", "contact", "load", "units"}
    ):
        return "runtime_remediation"
    return "evidence_expansion"


def _build_fixture_issue_samples() -> list[RawSample]:
    samples: list[RawSample] = []
    for expected_path in sorted(DIAG_FIXTURE_ROOT.rglob("expected.json")):
        case_dir = expected_path.parent
        inp_path = case_dir / "input.inp"
        stderr_path = case_dir / "stderr.txt"
        if not inp_path.exists() or not stderr_path.exists():
            continue
        expected = json.loads(_read_text(expected_path))
        inp_text = _clip_text(_read_text(inp_path), 1800)
        stderr_text = _clip_text(_read_text(stderr_path), 1800)
        case_id = str(expected.get("case_id") or case_dir.name)
        source_type = str(expected.get("source_type") or "synthetic")
        expected_issue_keys = [str(item) for item in list(expected.get("expected_issue_keys", []))]
        expected_severities = [str(item) for item in list(expected.get("expected_severities", []))]
        user = _normalize_text(
            f"""
            Task: Extract deterministic diagnosis labels from this CAE failure fixture.
            Case ID: {case_id}
            Source Type: {source_type}

            input.inp
            ```inp
            {inp_text}
            ```

            stderr.txt
            ```text
            {stderr_text}
            ```

            Return strict JSON only.
            """
        )
        assistant = {
            "case_id": case_id,
            "source_type": source_type,
            "expected_issue_keys": expected_issue_keys,
            "expected_severities": expected_severities,
            "primary_issue_key": _primary_issue_key(expected_issue_keys),
            "route_hint": _issue_route_hint(expected_issue_keys),
        }
        samples.append(
            RawSample(
                sample_id=f"fixture-{_sha1(case_id)[:12]}",
                task_type="issue_key_extraction",
                source_group="tests_fixture",
                source_ref=str(expected_path.relative_to(REPO_ROOT)),
                user=user,
                assistant=assistant,
                quality_score=1.0,
                tags=["fixture", "diagnosis", source_type],
            )
        )
    return samples


def _import_solver_summarizer():
    sys.path.insert(0, str(REPO_ROOT))
    from cae.ai.solver_output import summarize_solver_run  # type: ignore

    return summarize_solver_run


def _fallback_summarize_solver_run(results_dir: Path) -> dict[str, Any]:
    lower_names = {path.name.lower() for path in results_dir.glob("*")}
    solver = "unknown"
    if any("su2" in name for name in lower_names) or "history.csv" in lower_names:
        solver = "su2"
    elif any("openfoam" in name for name in lower_names) or (results_dir / "system" / "controlDict").exists():
        solver = "openfoam"
    elif any("code_aster" in name for name in lower_names) or any(path.suffix.lower() == ".comm" for path in results_dir.glob("*")):
        solver = "code_aster"
    elif any(path.suffix.lower() == ".sif" for path in results_dir.glob("*")):
        solver = "elmer"

    logs = sorted(path for path in results_dir.glob("*.log"))
    primary_log = logs[0] if logs else None
    status = "unknown"
    status_reason = None
    if primary_log is not None:
        log_text = _read_text(primary_log).lower()
        if any(token in log_text for token in ("fatal", "cannot find", "no such file", "error", "undefined")):
            status = "failed"
            status_reason = "fatal_or_missing_reference"
        elif any(token in log_text for token in ("not converged", "iterations reached", "max iterations")):
            status = "not_converged"
            status_reason = "max_iterations_before_convergence"
        elif any(token in log_text for token in ("exit success", "end", "arret normal", "diagnostic job : ok")):
            status = "success"
            status_reason = "normal_completion"

    return {
        "solver": solver,
        "status": status,
        "status_reason": status_reason,
        "primary_log": primary_log.name if primary_log is not None else None,
    }


def _collect_results_dirs() -> list[Path]:
    dirs: list[Path] = []
    for path in sorted(RESULTS_ROOT.iterdir()):
        if not path.is_dir():
            continue
        has_log = any(path.glob("*.log"))
        has_history = (path / "history.csv").exists()
        has_inputs = any(path.suffix.lower() in {".cfg", ".sif", ".comm"} for path in path.glob("*"))
        if has_log or has_history or has_inputs:
            dirs.append(path)
    return dirs


def _build_solver_run_samples() -> list[RawSample]:
    samples: list[RawSample] = []
    summarize_solver_run = None
    try:
        summarize_solver_run = _import_solver_summarizer()
    except Exception:
        summarize_solver_run = None

    for results_dir in _collect_results_dirs():
        if summarize_solver_run is not None:
            try:
                summary = summarize_solver_run(results_dir)
            except Exception:
                summary = _fallback_summarize_solver_run(results_dir)
        else:
            summary = _fallback_summarize_solver_run(results_dir)

        solver = str(summary.get("solver") or "unknown")
        status = str(summary.get("status") or "unknown")
        if status not in {"failed", "not_converged", "success", "unknown"}:
            status = "unknown"
        primary_log_name = str(summary.get("primary_log") or "")
        primary_log = results_dir / primary_log_name if primary_log_name else None

        snippets: list[str] = []
        if primary_log is not None and primary_log.exists():
            snippets.append(f"[{primary_log.name}]\n{_extract_key_log_snippet(_read_text(primary_log))}")
        history_csv = results_dir / "history.csv"
        if history_csv.exists():
            snippets.append(f"[history.csv]\n{_extract_key_log_snippet(_read_text(history_csv), max_lines=28)}")
        if not snippets:
            continue

        route = _route_for_solver_status(status)
        evidence_block = "\n\n".join(snippets)
        user = _normalize_text(
            f"""
            Task: Infer solver run summary and route decision.
            Results Directory: {results_dir.name}

            Evidence snippets:
            {evidence_block}

            Return strict JSON with keys:
            solver, status, route, primary_log, status_reason, next_action.
            """
        )
        assistant = {
            "solver": solver,
            "status": status,
            "route": route,
            "primary_log": primary_log.name if primary_log is not None and primary_log.exists() else None,
            "status_reason": summary.get("status_reason"),
            "next_action": _next_action_for_route(route),
        }
        samples.append(
            RawSample(
                sample_id=f"solver-run-{results_dir.name}",
                task_type="solver_route_decision",
                source_group="results_logs",
                source_ref=str(results_dir.relative_to(REPO_ROOT)),
                user=user,
                assistant=assistant,
                quality_score=0.96 if status != "unknown" else 0.86,
                tags=["solver_run", solver, status],
            )
        )
    return samples


def _infer_status_from_reason(reason: str | None) -> tuple[str, float]:
    if reason is None:
        return "unknown", 0.82
    lowered = reason.lower()
    if "frd result file detected" in lowered:
        return "success", 0.98
    if any(token in lowered for token in ("max iterations", "before convergence")):
        return "not_converged", 0.96
    if any(token in lowered for token in ("fatal", "cannot find", "no such file", "undefined", "not found", "error")):
        return "failed", 0.95
    if any(token in lowered for token in ("success", "normal")):
        return "success", 0.9
    return "unknown", 0.8


def _build_test_reason_samples() -> list[RawSample]:
    test_path = TESTS_ROOT / "test_mcp_server.py"
    text = _read_text(test_path)
    reason_pattern = re.compile(r'"status_reason"\s*:\s*(None|"([^"]*)")')
    unique_reasons: set[str | None] = set()
    for match in reason_pattern.finditer(text):
        if match.group(1) == "None":
            unique_reasons.add(None)
        else:
            unique_reasons.add(match.group(2) or "")

    samples: list[RawSample] = []
    for idx, reason in enumerate(sorted(unique_reasons, key=lambda item: "" if item is None else item)):
        status, confidence = _infer_status_from_reason(reason)
        route = _route_for_solver_status(status)
        user_reason = reason if reason is not None else "None"
        user = _normalize_text(
            f"""
            Task: Map runtime `status_reason` to `solver_status` and next route.
            Source: tests/test_mcp_server.py
            status_reason: {user_reason}

            Return strict JSON with keys:
            solver_status, route, next_action.
            """
        )
        assistant = {
            "solver_status": status,
            "route": route,
            "next_action": _next_action_for_route(route),
        }
        samples.append(
            RawSample(
                sample_id=f"test-reason-{idx:03d}",
                task_type="status_reason_routing",
                source_group="tests_status_reason",
                source_ref=str(test_path.relative_to(REPO_ROOT)),
                user=user,
                assistant=assistant,
                quality_score=confidence,
                tags=["mcp_server_test", status],
            )
        )
    return samples


def _guarded_executor_supported(
    target_file: str,
    operation_kind: str,
    selector_mode: str,
) -> tuple[bool, str]:
    key = (operation_kind, selector_mode)
    supported_pairs = {
        ("rewrite_declared_paths", "export_reference_entries"),
        ("restore_required_layout", "required_case_paths"),
        ("rename_declared_symbols", "patch_name_entries"),
        ("repair_missing_entries", "patch_field_entries"),
    }
    if key in supported_pairs:
        return True, "supported_by_guarded_executor_whitelist"
    if key == ("repair_dictionary_references", "dictionary_reference_entries"):
        if target_file in {"system/controlDict", "system/fvSolution"}:
            return True, "supported_for_openfoam_dictionary_subset"
        return False, "dictionary_subset_requires_controlDict_or_fvSolution"
    return False, "preview_only_or_not_whitelisted"


def _build_guarded_operation_samples() -> list[RawSample]:
    test_path = TESTS_ROOT / "test_mcp_server.py"
    lines = _read_text(test_path).splitlines()
    combos: set[tuple[str, str, str]] = set()
    for idx, line in enumerate(lines):
        target_match = re.search(r'if item\["target_files"\] == \["([^"]+)"\]', line)
        if target_match is None:
            continue
        target_file = target_match.group(1).strip()
        operation_kind = ""
        selector_mode = ""
        for look_ahead in range(idx, min(idx + 16, len(lines))):
            op_match = re.search(r'operation\.get\("operation_kind"\)\s*==\s*"([^"]+)"', lines[look_ahead])
            if op_match is not None:
                operation_kind = op_match.group(1).strip()
            mode_match = re.search(r'operation\.get\("selector_mode"\)\s*==\s*"([^"]+)"', lines[look_ahead])
            if mode_match is not None:
                selector_mode = mode_match.group(1).strip()
        if operation_kind and selector_mode:
            combos.add((target_file, operation_kind, selector_mode))

    samples: list[RawSample] = []
    for idx, (target_file, operation_kind, selector_mode) in enumerate(sorted(combos)):
        supported, reason = _guarded_executor_supported(
            target_file=target_file,
            operation_kind=operation_kind,
            selector_mode=selector_mode,
        )
        user = _normalize_text(
            f"""
            Task: Decide if this runtime remediation operation should execute through guarded write.
            Source: tests/test_mcp_server.py
            target_file: {target_file}
            operation_kind: {operation_kind}
            selector_mode: {selector_mode}

            Return strict JSON with keys:
            executor_supported, decision_reason.
            """
        )
        assistant = {
            "executor_supported": supported,
            "decision_reason": reason,
        }
        samples.append(
            RawSample(
                sample_id=f"guarded-op-{idx:03d}",
                task_type="guarded_executor_decision",
                source_group="tests_guarded_operations",
                source_ref=str(test_path.relative_to(REPO_ROOT)),
                user=user,
                assistant=assistant,
                quality_score=0.95,
                tags=["guarded_executor", operation_kind, selector_mode],
            )
        )
    return samples


def _build_devlog_samples() -> list[RawSample]:
    text = _read_text(DEV_LOG_PATH)
    bullets = [
        line[2:].strip()
        for line in text.splitlines()
        if line.startswith("- ")
    ]
    guarded_lines = [
        line
        for line in bullets
        if "guarded" in line.lower()
        or "execute_guarded_edit_plan" in line
        or "dry_run_validation" in line
    ]
    if not guarded_lines:
        return []
    excerpt = guarded_lines[:16]
    user = _normalize_text(
        f"""
        Task: Build a compact guarded-executor capability summary from project development memory.
        Source: DEVELOPMENT_LOG.md

        Milestones:
        {chr(10).join(f"- {line}" for line in excerpt)}

        Return strict JSON with keys:
        capabilities, test_anchor, next_focus.
        """
    )
    capabilities: list[str] = []
    joined = " ".join(excerpt).lower()
    if "bounded numeric parameter" in joined:
        capabilities.append("bounded_numeric_parameter_update")
    if "code_aster" in joined and ".export" in joined:
        capabilities.append("code_aster_export_reference_rewrite")
    if "restore_case_layout" in joined or "required `0/`, `constant/`, and `system/`" in joined:
        capabilities.append("openfoam_required_case_layout_restore")
    if "writeinterval" in joined:
        capabilities.append("openfoam_controlDict_writeInterval_restore")
    if "relaxationfactors" in joined:
        capabilities.append("openfoam_fvSolution_relaxationFactors_restore")
    if "patch_name_entries" in joined:
        capabilities.append("openfoam_patch_name_entries_rename")
    if "patch_field_entries" in joined:
        capabilities.append("openfoam_patch_field_entries_repair")

    next_focus = "Expand guarded executor coverage with single-surface, backup-first constraints."
    for line in text.splitlines():
        if line.strip().startswith("- ") and "Extend guarded execution beyond" in line:
            next_focus = line.strip()[2:].strip()
            break

    samples = [
        RawSample(
            sample_id="devlog-guarded-capability-summary",
            task_type="capability_grounding",
            source_group="development_log",
            source_ref=str(DEV_LOG_PATH.relative_to(REPO_ROOT)),
            user=user,
            assistant={
                "capabilities": capabilities,
                "test_anchor": "54 passed",
                "next_focus": next_focus,
            },
            quality_score=0.92,
            tags=["development_log", "guarded_executor"],
        )
    ]
    return samples


def _infer_solver_from_example_path(path: Path) -> str:
    lower = str(path).lower()
    if "su2" in lower or path.suffix.lower() == ".cfg":
        return "su2"
    if path.suffix.lower() == ".sif":
        return "elmer"
    if path.suffix.lower() == ".comm":
        return "code_aster"
    if "openfoam" in lower or path.name in {"controlDict", "fvSolution", "fvSchemes"}:
        return "openfoam"
    return "unknown"


def _build_smoke_case_samples() -> list[RawSample]:
    candidate_paths = [
        EXAMPLES_ROOT / "su2_inviscid_bump" / "inv_channel_smoke.cfg",
        EXAMPLES_ROOT / "su2_elasticity_smoke" / "case.cfg",
        EXAMPLES_ROOT / "elmer_steady_heat" / "case.sif",
        EXAMPLES_ROOT / "code_aster_minimal_smoke" / "case.comm",
        EXAMPLES_ROOT / "openfoam_cavity_smoke" / "system" / "controlDict",
    ]
    samples: list[RawSample] = []
    for path in candidate_paths:
        if not path.exists():
            continue
        solver = _infer_solver_from_example_path(path)
        file_text = _clip_text(_read_text(path), 1700)
        user = _normalize_text(
            f"""
            Task: Identify solver family and parse smoke-input profile.
            Source file: {path.relative_to(REPO_ROOT)}

            ```text
            {file_text}
            ```

            Return strict JSON with keys:
            solver, input_kind, likely_primary_log.
            """
        )
        likely_primary_log = {
            "su2": "docker-su2.log",
            "openfoam": "docker-openfoam.log",
            "code_aster": "docker-code_aster.log",
            "elmer": "solver.log",
        }.get(solver)
        assistant = {
            "solver": solver,
            "input_kind": path.suffix.lower().lstrip(".") or path.name,
            "likely_primary_log": likely_primary_log,
        }
        samples.append(
            RawSample(
                sample_id=f"smoke-{_sha1(str(path.relative_to(REPO_ROOT)))[:12]}",
                task_type="smoke_input_profiling",
                source_group="solver_smoke_case",
                source_ref=str(path.relative_to(REPO_ROOT)),
                user=user,
                assistant=assistant,
                quality_score=0.9 if solver != "unknown" else 0.8,
                tags=["smoke_case", solver],
            )
        )
    return samples


def _extract_prompt_field(text: str, field_name: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(field_name)}\s*:\s*(.+)$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return None
    return match.group(1).strip()


def _risk_from_severities(severities: list[str]) -> str:
    lowered = {item.lower() for item in severities}
    if "error" in lowered:
        return "high"
    if "warning" in lowered:
        return "medium"
    return "low"


def _build_fixture_route_samples(base_samples: list[RawSample]) -> list[RawSample]:
    templates = [
        "Map fixture issue labels into a deterministic routing lane.",
        "Infer triage lane from expected issue keys and severity profile.",
        "Produce issue-to-route planning summary for downstream guarded remediation.",
    ]
    samples: list[RawSample] = []
    for sample in base_samples:
        case_id = str(sample.assistant.get("case_id") or "unknown_case")
        source_type = str(sample.assistant.get("source_type") or "synthetic")
        issue_keys = [str(item) for item in list(sample.assistant.get("expected_issue_keys", []))]
        severities = [str(item) for item in list(sample.assistant.get("expected_severities", []))]
        primary_issue_key = _primary_issue_key(issue_keys)
        route_hint = _issue_route_hint(issue_keys)
        risk_level = _risk_from_severities(severities)
        for idx, template in enumerate(templates):
            user = _normalize_text(
                f"""
                Task: {template}
                Case ID: {case_id}
                Source Type: {source_type}
                expected_issue_keys: {json.dumps(issue_keys, ensure_ascii=False)}
                expected_severities: {json.dumps(severities, ensure_ascii=False)}

                Use deterministic routing rules aligned with the diagnosis guardrails.
                Return strict JSON with keys:
                case_id, primary_issue_key, route_hint, risk_level, triage_lane.
                """
            )
            assistant = {
                "case_id": case_id,
                "primary_issue_key": primary_issue_key,
                "route_hint": route_hint,
                "risk_level": risk_level,
                "triage_lane": "safe_auto_fix" if risk_level != "high" else "blocking",
            }
            samples.append(
                RawSample(
                    sample_id=f"{sample.sample_id}-route-{idx}",
                    task_type="fixture_route_mapping",
                    source_group=sample.source_group,
                    source_ref=sample.source_ref,
                    user=user,
                    assistant=assistant,
                    quality_score=0.95,
                    tags=[*sample.tags, "augmented", "route_mapping"],
                )
            )
    return samples


def _build_status_reason_augmented_samples(base_samples: list[RawSample]) -> list[RawSample]:
    templates = [
        "Classify `status_reason` into a solver status gate for Agent routing.",
        "Normalize runtime reason text into route lane and safe next action.",
        "Infer routing decision from runtime reason with strict deterministic policy.",
        "Map raw status_reason to remediation lane before physics interpretation.",
        "Convert runtime reason fragment into solver_status and route handoff.",
        "Generate runtime gate output for orchestration from status_reason text.",
        "Resolve status_reason into route and bounded next action for Agent.",
        "Build status_reason routing payload for guarded diagnose workflow.",
    ]
    samples: list[RawSample] = []
    for sample in base_samples:
        reason = _extract_prompt_field(sample.user, "status_reason") or "None"
        status = str(sample.assistant.get("solver_status") or "unknown")
        route = str(sample.assistant.get("route") or _route_for_solver_status(status))
        next_action = str(sample.assistant.get("next_action") or _next_action_for_route(route))
        for idx, template in enumerate(templates):
            user = _normalize_text(
                f"""
                Task: {template}
                Source: tests/test_mcp_server.py
                status_reason: {reason}

                Policy:
                - failed -> runtime_remediation
                - not_converged -> convergence_tuning
                - success -> physics_diagnosis
                - unknown -> evidence_expansion

                Return strict JSON with keys:
                solver_status, route, next_action, gate_priority.
                """
            )
            assistant = {
                "solver_status": status,
                "route": route,
                "next_action": next_action,
                "gate_priority": {
                    "runtime_remediation": 1,
                    "convergence_tuning": 2,
                    "physics_diagnosis": 3,
                    "evidence_expansion": 1,
                }.get(route, 1),
            }
            samples.append(
                RawSample(
                    sample_id=f"{sample.sample_id}-sr-aug-{idx}",
                    task_type="status_reason_routing_augmented",
                    source_group=sample.source_group,
                    source_ref=sample.source_ref,
                    user=user,
                    assistant=assistant,
                    quality_score=max(0.84, min(0.98, sample.quality_score)),
                    tags=[*sample.tags, "augmented", "status_reason_policy"],
                )
            )
    return samples


def _build_solver_run_augmented_samples(base_samples: list[RawSample]) -> list[RawSample]:
    templates = [
        "Build solver gate decision from summarized run evidence.",
        "Convert solver run summary into route and blocked action policy.",
        "Infer orchestration lane from solver run status metadata.",
        "Generate route handoff payload from solver run summary.",
        "Map run summary to next diagnostic branch and execution intent.",
        "Prepare deterministic routing context from run-level evidence.",
        "Resolve solver run status into lane and guarded next action.",
        "Compose route summary for Agent from solver execution snapshot.",
    ]
    blocked_actions = {
        "runtime_remediation": ["physics_diagnosis", "auto_fix_without_runtime_confirmation"],
        "convergence_tuning": ["physics_diagnosis_as_final_answer"],
        "physics_diagnosis": [],
        "evidence_expansion": ["physics_diagnosis", "auto_fix_without_classification"],
    }
    samples: list[RawSample] = []
    for sample in base_samples:
        solver = str(sample.assistant.get("solver") or "unknown")
        status = str(sample.assistant.get("status") or "unknown")
        route = str(sample.assistant.get("route") or _route_for_solver_status(status))
        primary_log = sample.assistant.get("primary_log")
        status_reason = sample.assistant.get("status_reason")
        next_action = str(sample.assistant.get("next_action") or _next_action_for_route(route))
        results_dir = Path(sample.source_ref).name
        for idx, template in enumerate(templates):
            user = _normalize_text(
                f"""
                Task: {template}
                Results Directory: {results_dir}
                solver: {solver}
                status: {status}
                primary_log: {primary_log}
                status_reason: {status_reason}

                Return strict JSON with keys:
                solver, status, route, blocked_actions, next_action.
                """
            )
            assistant = {
                "solver": solver,
                "status": status,
                "route": route,
                "blocked_actions": blocked_actions.get(route, []),
                "next_action": next_action,
            }
            samples.append(
                RawSample(
                    sample_id=f"{sample.sample_id}-run-aug-{idx}",
                    task_type="solver_route_decision_augmented",
                    source_group=sample.source_group,
                    source_ref=sample.source_ref,
                    user=user,
                    assistant=assistant,
                    quality_score=max(0.86, min(0.98, sample.quality_score)),
                    tags=[*sample.tags, "augmented", "solver_gate"],
                )
            )
    return samples


def _build_smoke_case_augmented_samples(base_samples: list[RawSample]) -> list[RawSample]:
    templates = [
        "Infer runtime validation checklist from smoke input profile.",
        "Map smoke-input metadata into expected primary log and artifact hints.",
        "Generate solver-specific preflight checks from input-kind summary.",
        "Build smoke-case interpretation payload for multi-solver routing.",
        "Classify smoke input into solver family and expected diagnostics hooks.",
        "Derive deterministic smoke run checks for downstream diagnose orchestration.",
    ]
    checks_by_solver = {
        "su2": ["inspect history.csv residuals", "validate CFL and EXT_ITER", "verify mesh sidecar files"],
        "openfoam": ["verify 0/ constant/ system/ layout", "inspect controlDict and fvSolution", "check boundary patch entries"],
        "code_aster": ["verify .export declared references", "confirm .comm sidecar path consistency", "inspect docker-code_aster.log"],
        "elmer": ["confirm .sif section integrity", "check solver.log for normal completion", "validate produced VTU artifacts"],
        "unknown": ["collect primary log", "enumerate artifacts", "expand evidence before routing"],
    }
    result_hint_by_solver = {
        "su2": "history.csv",
        "openfoam": "time-step directories (e.g. 0.1/)",
        "code_aster": "message/med outputs declared by .export",
        "elmer": "VTU/EP outputs from Elmer case",
        "unknown": "runtime-dependent",
    }
    samples: list[RawSample] = []
    for sample in base_samples:
        solver = str(sample.assistant.get("solver") or "unknown")
        input_kind = str(sample.assistant.get("input_kind") or "unknown")
        likely_primary_log = sample.assistant.get("likely_primary_log")
        source_file = sample.source_ref
        checks = checks_by_solver.get(solver, checks_by_solver["unknown"])
        result_hint = result_hint_by_solver.get(solver, result_hint_by_solver["unknown"])
        for idx, template in enumerate(templates):
            user = _normalize_text(
                f"""
                Task: {template}
                Source file: {source_file}
                solver: {solver}
                input_kind: {input_kind}
                likely_primary_log: {likely_primary_log}

                Return strict JSON with keys:
                solver, input_kind, likely_primary_log, expected_result_artifact, recommended_checks.
                """
            )
            assistant = {
                "solver": solver,
                "input_kind": input_kind,
                "likely_primary_log": likely_primary_log,
                "expected_result_artifact": result_hint,
                "recommended_checks": checks,
            }
            samples.append(
                RawSample(
                    sample_id=f"{sample.sample_id}-smoke-aug-{idx}",
                    task_type="smoke_input_profiling_augmented",
                    source_group=sample.source_group,
                    source_ref=sample.source_ref,
                    user=user,
                    assistant=assistant,
                    quality_score=max(0.86, sample.quality_score),
                    tags=[*sample.tags, "augmented", "smoke_preflight"],
                )
            )
    return samples


def _build_status_route_policy_samples() -> list[RawSample]:
    reasons_by_status = {
        "failed": [
            "FOAM FATAL ERROR: cannot find patchField entry",
            "no such file or directory while loading mesh sidecar",
            "undefined reference in runtime dictionary include",
            "solver aborted with fatal runtime exception",
            "docker runtime error: mount path not found",
            "permission denied writing result file",
            "runtime image command failed before iterations",
            "input parse error: missing required section",
            "material card malformed and parser stopped",
            "cannot read declared export reference file",
        ],
        "not_converged": [
            "maximum iterations reached before convergence",
            "residual plateau above tolerance threshold",
            "CFL growth caused instability and stop",
            "linear solver stagnated after iteration budget",
            "nonlinear loop stopped at iteration cap",
            "time step repeatedly reduced without convergence",
            "residual trend improving but not converged",
            "solver stopped after max ext_iter",
            "increment cutbacks exhausted convergence budget",
            "residual oscillation detected at final step",
        ],
        "success": [
            "diagnostic job : ok",
            "normal completion and output artifacts written",
            "exit success with result files detected",
            "solver completed with no fatal warnings",
            "run finished and produced final step outputs",
            "normal termination in solver log",
            "completed all steps within tolerance",
            "run ended successfully with expected artifacts",
            "simulation completed and logs closed cleanly",
            "analysis finished with stable residual end-state",
        ],
        "unknown": [
            "primary log missing from results directory",
            "insufficient runtime metadata to classify status",
            "no residual or completion markers found",
            "artifact set incomplete and ambiguous",
            "mixed signals in logs without dominant failure",
            "status reason unavailable",
            "partial logs collected from interrupted run",
            "result files absent and no fatal marker",
            "runtime trace truncated before decision point",
            "evidence not enough for deterministic classification",
        ],
    }
    blocked_actions = {
        "runtime_remediation": ["physics_diagnosis", "auto_fix_without_runtime_confirmation"],
        "convergence_tuning": ["physics_diagnosis_as_final_answer"],
        "physics_diagnosis": [],
        "evidence_expansion": ["physics_diagnosis", "auto_fix_without_classification"],
    }
    samples: list[RawSample] = []
    for status, reasons in reasons_by_status.items():
        route = _route_for_solver_status(status)
        for idx, reason in enumerate(reasons):
            user = _normalize_text(
                f"""
                Task: Apply the global solver-status routing policy.
                status_reason: {reason}
                candidate_status: {status}

                Policy:
                failed -> runtime_remediation
                not_converged -> convergence_tuning
                success -> physics_diagnosis
                unknown -> evidence_expansion

                Return strict JSON with keys:
                solver_status, route, blocked_actions, next_action.
                """
            )
            assistant = {
                "solver_status": status,
                "route": route,
                "blocked_actions": blocked_actions.get(route, []),
                "next_action": _next_action_for_route(route),
            }
            samples.append(
                RawSample(
                    sample_id=f"route-policy-{status}-{idx:02d}",
                    task_type="status_route_policy",
                    source_group="routing_policy",
                    source_ref="synthetic/status_route_policy",
                    user=user,
                    assistant=assistant,
                    quality_score=0.93,
                    tags=["policy", status, route],
                )
            )
    return samples


def _build_guarded_operation_augmented_samples(base_samples: list[RawSample]) -> list[RawSample]:
    templates = [
        "Evaluate guarded write eligibility for one remediation operation.",
        "Classify operation support under guarded executor whitelist rules.",
        "Decide whether this operation can leave preview-only mode.",
        "Map operation signature to guarded executor support outcome.",
        "Infer write-guard compatibility from operation/selector pair.",
        "Generate executor support decision for remediation operation.",
        "Determine if operation is whitelisted for guarded execution.",
        "Produce guarded executor routing decision for selected operation.",
    ]
    samples: list[RawSample] = []
    for sample in base_samples:
        target_file = _extract_prompt_field(sample.user, "target_file") or "unknown_target"
        operation_kind = _extract_prompt_field(sample.user, "operation_kind") or "unknown_operation"
        selector_mode = _extract_prompt_field(sample.user, "selector_mode") or "unknown_selector"
        supported = bool(sample.assistant.get("executor_supported"))
        decision_reason = str(sample.assistant.get("decision_reason") or "unknown_reason")
        for idx, template in enumerate(templates):
            user = _normalize_text(
                f"""
                Task: {template}
                target_file: {target_file}
                operation_kind: {operation_kind}
                selector_mode: {selector_mode}

                Return strict JSON with keys:
                executor_supported, decision_reason, required_guard.
                """
            )
            assistant = {
                "executor_supported": supported,
                "decision_reason": decision_reason,
                "required_guard": "dry_run_validation + backup_first_single_surface_write",
            }
            samples.append(
                RawSample(
                    sample_id=f"{sample.sample_id}-guard-aug-{idx}",
                    task_type="guarded_executor_decision_augmented",
                    source_group=sample.source_group,
                    source_ref=sample.source_ref,
                    user=user,
                    assistant=assistant,
                    quality_score=0.93,
                    tags=[*sample.tags, "augmented", "guarded_policy"],
                )
            )
    return samples


def _deduplicate_and_filter(samples: list[RawSample], min_quality_score: float) -> list[RawSample]:
    deduped: list[RawSample] = []
    seen: set[str] = set()
    for sample in samples:
        if sample.quality_score < min_quality_score:
            continue
        user = _normalize_text(sample.user)
        assistant_text = json.dumps(sample.assistant, ensure_ascii=False, sort_keys=True)
        if len(user) < 80 or len(user) > 9000:
            continue
        if len(assistant_text) < 18:
            continue
        key = _sha1(f"{sample.task_type}\n{user}\n{assistant_text}")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            RawSample(
                sample_id=sample.sample_id,
                task_type=sample.task_type,
                source_group=sample.source_group,
                source_ref=sample.source_ref,
                user=user,
                assistant=sample.assistant,
                quality_score=sample.quality_score,
                tags=sample.tags,
            )
        )
    return deduped


def _assign_splits(samples: list[RawSample], seed: int) -> dict[str, list[RawSample]]:
    rng = random.Random(seed)
    by_task: dict[str, list[RawSample]] = {}
    for sample in samples:
        by_task.setdefault(sample.task_type, []).append(sample)
    split_map: dict[str, list[RawSample]] = {"train": [], "val": [], "test": []}
    for task_type, task_samples in by_task.items():
        shuffled = list(task_samples)
        rng.shuffle(shuffled)
        n = len(shuffled)
        if n <= 2:
            split_map["train"].extend(shuffled)
            continue
        if n <= 5:
            split_map["train"].extend(shuffled[:-1])
            split_map["val"].append(shuffled[-1])
            continue
        n_val = max(1, round(n * 0.12))
        n_test = max(1, round(n * 0.12))
        n_train = n - n_val - n_test
        if n_train < 1:
            n_train = 1
            n_val = max(1, n_val - 1)
        split_map["train"].extend(shuffled[:n_train])
        split_map["val"].extend(shuffled[n_train : n_train + n_val])
        split_map["test"].extend(shuffled[n_train + n_val :])
    return split_map


def _record_dict(sample: RawSample, split: str) -> dict[str, Any]:
    assistant_text = json.dumps(sample.assistant, ensure_ascii=False, sort_keys=True)
    return {
        "id": sample.sample_id,
        "split": split,
        "task_type": sample.task_type,
        "source_group": sample.source_group,
        "source_ref": sample.source_ref,
        "quality_score": round(float(sample.quality_score), 4),
        "tags": sample.tags,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": sample.user},
            {"role": "assistant", "content": assistant_text},
        ],
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for record in records:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_chat_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for record in records:
            fp.write(json.dumps({"messages": record["messages"]}, ensure_ascii=False) + "\n")


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        label = str(record.get(key) or "unknown")
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _build_manifest(all_records: list[dict[str, Any]], min_quality_score: float) -> dict[str, Any]:
    split_counts = _count_by(all_records, "split")
    task_counts = _count_by(all_records, "task_type")
    source_counts = _count_by(all_records, "source_group")
    return {
        "dataset_name": DATASET_NAME,
        "record_count": len(all_records),
        "split_counts": split_counts,
        "task_type_counts": task_counts,
        "source_group_counts": source_counts,
        "system_prompt": SYSTEM_PROMPT,
        "quality_filters": {
            "min_quality_score": round(float(min_quality_score), 4),
            "min_user_chars": 80,
            "max_user_chars": 9000,
            "dedupe": "sha1(task_type + normalized_user + assistant_json)",
        },
    }


def _write_readme(path: Path, manifest: dict[str, Any], hq_threshold: float) -> None:
    text = f"""# CAE CLI Fine-tune Dataset v2

This dataset was exported from local project assets:

- `tests/fixtures/diagnosis_cases` (high-confidence expected labels)
- `results/*` solver logs and smoke outputs
- `tests/test_mcp_server.py` status reasons and guarded operation patterns
- `DEVELOPMENT_LOG.md` guarded executor capability milestones
- `examples/*` solver smoke input files
- deterministic policy augmentations aligned to solver status routing and guarded write boundaries

## Summary

- record_count: {manifest["record_count"]}
- split_counts: {json.dumps(manifest["split_counts"], ensure_ascii=False)}
- task_type_counts: {json.dumps(manifest["task_type_counts"], ensure_ascii=False)}
- source_group_counts: {json.dumps(manifest["source_group_counts"], ensure_ascii=False)}

## Files

- `all.jsonl`: full rich records with metadata and `messages`
- `train.jsonl`, `val.jsonl`, `test.jsonl`: rich split records
- `train_chat.jsonl`, `val_chat.jsonl`, `test_chat.jsonl`: chat-only records for common finetune toolchains
- `train_hq.jsonl`, `val_hq.jsonl`, `test_hq.jsonl`: rich high-quality subset (quality_score >= {hq_threshold})
- `train_hq_chat.jsonl`, `val_hq_chat.jsonl`, `test_hq_chat.jsonl`: chat-only high-quality subset
- `manifest.json`: counts and quality filter metadata
- `manifest_hq.json`: high-quality subset counts and threshold
"""
    path.write_text(text, encoding="utf-8")


def _write_hq_subset(
    output_dir: Path,
    all_records: list[dict[str, Any]],
    hq_min_quality: float,
) -> dict[str, Any]:
    hq_records = [
        record
        for record in all_records
        if float(record.get("quality_score", 0.0)) >= hq_min_quality
    ]
    by_split: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    for record in hq_records:
        split = str(record.get("split") or "train")
        if split not in by_split:
            split = "train"
        by_split[split].append(record)
    for split, records in by_split.items():
        _write_jsonl(output_dir / f"{split}_hq.jsonl", records)
        _write_chat_jsonl(output_dir / f"{split}_hq_chat.jsonl", records)
    hq_manifest = {
        "dataset_name": DATASET_HQ_NAME,
        "hq_min_quality": round(float(hq_min_quality), 4),
        "record_count": len(hq_records),
        "split_counts": _count_by(hq_records, "split"),
        "task_type_counts": _count_by(hq_records, "task_type"),
        "source_group_counts": _count_by(hq_records, "source_group"),
    }
    (output_dir / "manifest_hq.json").write_text(
        json.dumps(hq_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return hq_manifest


def export_dataset(output_dir: Path, seed: int, min_quality_score: float, hq_min_quality: float) -> dict[str, Any]:
    fixture_samples = _build_fixture_issue_samples()
    solver_run_samples = _build_solver_run_samples()
    test_reason_samples = _build_test_reason_samples()
    guarded_operation_samples = _build_guarded_operation_samples()
    devlog_samples = _build_devlog_samples()
    smoke_case_samples = _build_smoke_case_samples()

    raw_samples: list[RawSample] = []
    raw_samples.extend(fixture_samples)
    raw_samples.extend(solver_run_samples)
    raw_samples.extend(test_reason_samples)
    raw_samples.extend(guarded_operation_samples)
    raw_samples.extend(devlog_samples)
    raw_samples.extend(smoke_case_samples)

    # Controlled augmentations: increase corpus coverage while staying aligned to
    # deterministic routing and guarded-write policies extracted from real assets.
    raw_samples.extend(_build_fixture_route_samples(fixture_samples))
    raw_samples.extend(_build_status_reason_augmented_samples(test_reason_samples))
    raw_samples.extend(_build_solver_run_augmented_samples(solver_run_samples))
    raw_samples.extend(_build_smoke_case_augmented_samples(smoke_case_samples))
    raw_samples.extend(_build_guarded_operation_augmented_samples(guarded_operation_samples))
    raw_samples.extend(_build_status_route_policy_samples())

    filtered = _deduplicate_and_filter(raw_samples, min_quality_score=min_quality_score)
    split_samples = _assign_splits(filtered, seed=seed)

    all_records: list[dict[str, Any]] = []
    for split, samples in split_samples.items():
        records = [_record_dict(sample, split=split) for sample in samples]
        all_records.extend(records)
        _write_jsonl(output_dir / f"{split}.jsonl", records)
        _write_chat_jsonl(output_dir / f"{split}_chat.jsonl", records)

    all_records = sorted(all_records, key=lambda item: (item["split"], item["task_type"], item["id"]))
    _write_jsonl(output_dir / "all.jsonl", all_records)
    manifest = _build_manifest(all_records, min_quality_score=min_quality_score)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    hq_manifest = _write_hq_subset(output_dir, all_records, hq_min_quality=hq_min_quality)
    _write_readme(output_dir / "README.md", manifest, hq_threshold=hq_manifest["hq_min_quality"])
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export CAE CLI fine-tune dataset.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory for dataset files.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260423,
        help="Random seed for deterministic split assignment.",
    )
    parser.add_argument(
        "--min-quality-score",
        type=float,
        default=0.75,
        help="Minimum quality_score retained before split assignment.",
    )
    parser.add_argument(
        "--hq-min-quality",
        type=float,
        default=0.9,
        help="Minimum quality_score for high-quality subset export.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    manifest = export_dataset(
        output_dir=args.output_dir,
        seed=args.seed,
        min_quality_score=args.min_quality_score,
        hq_min_quality=args.hq_min_quality,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
