from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

import cae.mcp_server as mcp_server
from cae.ai.diagnose import DiagnoseResult
from cae.docker import DockerSolverRunResult
from cae.mcp_server import (
    tool_convergence_tuning,
    tool_convergence_parameter_suggestions,
    tool_convergence_tuning_prompt,
    tool_diagnose,
    tool_docker_calculix,
    tool_docker_build_su2_runtime,
    tool_docker_catalog,
    tool_docker_images,
    tool_docker_pull,
    tool_docker_recommend,
    tool_docker_run,
    tool_docker_status,
    tool_execute_guarded_edit_plan,
    tool_evidence_collection_plan,
    tool_evidence_expansion,
    tool_health,
    tool_inp_check,
    tool_physics_interpretation_prompt,
    tool_physics_diagnosis,
    tool_runtime_remediation,
    tool_runtime_remediation_prompt,
    tool_runtime_retry_checks,
    tool_selected_edit_execution_plan,
    tool_solve,
)
from cae.solvers.base import SolveResult
from cae.runtimes.docker import ContainerRunResult


@pytest.fixture
def workspace() -> Iterator[Path]:
    root = Path(__file__).parent / ".tmp_mcp_server"
    root.mkdir(exist_ok=True)
    path = root / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_tool_health_returns_solver_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        "cae.mcp_server.list_solvers",
        lambda: [
            {
                "name": "calculix",
                "installed": True,
                "version": "2.23",
                "formats": [".inp"],
                "description": "CalculiX",
            }
        ],
    )

    payload = tool_health()

    assert payload["ok"] is True
    assert payload["data"]["service"] == "cae-cli-mcp"
    assert "calculix" in payload["data"]["installed_solvers"]


def test_tool_solve_returns_error_for_missing_inp() -> None:
    payload = tool_solve(inp_file="D:/not-exists/abc.inp")

    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_tool_solve_returns_error_for_empty_inp() -> None:
    payload = tool_solve(inp_file="")

    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_input"


def test_tool_solve_returns_structured_result(monkeypatch, workspace: Path) -> None:
    inp = workspace / "model.inp"
    inp.write_text("*NODE\n1,0,0,0\n", encoding="utf-8")
    out_dir = workspace / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    frd = out_dir / "model.frd"
    frd.write_text("dummy", encoding="utf-8")

    class DummySolver:
        def solve(
            self,
            inp_file: Path,
            output_dir: Path,
            *,
            timeout: int = 3600,
            **kwargs,
        ):
            return SolveResult(
                success=True,
                output_dir=output_dir,
                output_files=[frd],
                stdout="ok",
                stderr="",
                returncode=0,
                duration_seconds=1.2,
                warnings=[],
            )

    monkeypatch.setattr("cae.mcp_server.get_solver", lambda name: DummySolver())

    payload = tool_solve(inp_file=str(inp), output_dir=str(out_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["success"] is True
    assert data["frd_file"] is not None
    assert data["returncode"] == 0


def test_tool_solve_does_not_persist_solver_path(monkeypatch, workspace: Path) -> None:
    monkeypatch.setattr(mcp_server.settings, "_data", {"solver_path": "original-ccx"})

    inp = workspace / "model.inp"
    inp.write_text("*NODE\n1,0,0,0\n", encoding="utf-8")
    out_dir = workspace / "results"
    fake_solver_path = workspace / "ccx.exe"
    fake_solver_path.write_text("fake", encoding="utf-8")

    class DummySolver:
        def solve(
            self,
            inp_file: Path,
            output_dir: Path,
            *,
            timeout: int = 3600,
            **kwargs,
        ):
            return SolveResult(
                success=True,
                output_dir=output_dir,
                output_files=[],
                stdout="ok",
                stderr="",
                returncode=0,
                duration_seconds=0.1,
            )

    monkeypatch.setattr("cae.mcp_server.get_solver", lambda name: DummySolver())

    payload = tool_solve(
        inp_file=str(inp),
        output_dir=str(out_dir),
        solver_path=str(fake_solver_path),
    )

    assert payload["ok"] is True
    assert mcp_server.settings._data["solver_path"] == "original-ccx"


def test_tool_solve_wraps_solver_exceptions(monkeypatch, workspace: Path) -> None:
    inp = workspace / "model.inp"
    inp.write_text("*NODE\n1,0,0,0\n", encoding="utf-8")

    class FailingSolver:
        def solve(
            self,
            inp_file: Path,
            output_dir: Path,
            *,
            timeout: int = 3600,
            **kwargs,
        ):
            raise RuntimeError("solver crashed")

    monkeypatch.setattr("cae.mcp_server.get_solver", lambda name: FailingSolver())

    payload = tool_solve(inp_file=str(inp), output_dir=str(workspace / "results"))

    assert payload["ok"] is False
    assert payload["error"]["code"] == "solve_failed"
    assert "solver crashed" in payload["error"]["message"]


def test_tool_docker_status_returns_standalone_runtime_info(monkeypatch) -> None:
    class DummyDockerRuntime:
        def inspect(self):
            return {
                "available": True,
                "version": "25.0.0",
                "backend": "wsl",
                "command": ["wsl", "-e", "docker"],
                "use_wsl_paths": True,
                "error": None,
            }

    monkeypatch.setattr("cae.mcp_server.DockerRuntime", DummyDockerRuntime)

    payload = tool_docker_status()

    assert payload["ok"] is True
    assert payload["data"]["backend"] == "wsl"
    assert payload["data"]["command"] == ["wsl", "-e", "docker"]


def test_tool_docker_catalog_returns_builtin_aliases() -> None:
    payload = tool_docker_catalog()

    assert payload["ok"] is True
    assert any(item["alias"] == "calculix" for item in payload["data"]["images"])
    assert any(item["alias"] == "openfoam" for item in payload["data"]["images"])
    assert any(item["alias"] == "code-aster" for item in payload["data"]["images"])


def test_tool_docker_catalog_can_filter_by_capability() -> None:
    payload = tool_docker_catalog(capability="cfd", include_experimental=False)

    assert payload["ok"] is True
    assert any(item["alias"] == "openfoam" for item in payload["data"]["images"])
    assert not any(item["alias"] == "su2" for item in payload["data"]["images"])

    runnable = tool_docker_catalog(solver="su2", runnable_only=True)
    assert runnable["ok"] is True
    assert any(item["alias"] == "su2-runtime" for item in runnable["data"]["images"])


def test_tool_docker_recommend_returns_candidates() -> None:
    payload = tool_docker_recommend(query="nonlinear structural contact", limit=3)

    assert payload["ok"] is True
    assert payload["data"]["recommendations"]
    assert payload["data"]["recommendations"][0]["solver"] in {"calculix", "code_aster"}


def test_tool_docker_images_lists_local_images(monkeypatch) -> None:
    class DummyDockerRuntime:
        def list_images(self):
            return ["unifem/calculix-desktop:latest"]

    monkeypatch.setattr("cae.mcp_server.DockerRuntime", DummyDockerRuntime)

    payload = tool_docker_images()

    assert payload["ok"] is True
    assert payload["data"]["images"] == ["unifem/calculix-desktop:latest"]


def test_tool_docker_pull_resolves_alias_and_can_set_default(monkeypatch) -> None:
    monkeypatch.setattr(mcp_server.settings, "_data", {})
    monkeypatch.setattr(
        mcp_server.settings,
        "set",
        lambda key, value: mcp_server.settings._data.__setitem__(key, value),
    )

    class DummyDockerRuntime:
        def image_exists(self, image):
            return False

        def pull_image(self, image, *, timeout=3600, use_default_config=False):
            assert image == "unifem/calculix-desktop:latest"
            assert timeout == 12
            assert use_default_config is False
            return ContainerRunResult(
                stdout="pulled",
                stderr="",
                returncode=0,
                duration_seconds=0.1,
                command=["wsl", "-e", "docker", "pull", image],
            )

    monkeypatch.setattr("cae.mcp_server.DockerRuntime", DummyDockerRuntime)

    payload = tool_docker_pull(image="calculix", timeout=12, set_default=True)

    assert payload["ok"] is True
    assert payload["data"]["image"] == "unifem/calculix-desktop:latest"
    assert payload["data"]["default_saved"] is True
    assert mcp_server.settings._data["docker_calculix_image"] == "unifem/calculix-desktop:latest"


def test_tool_docker_pull_can_save_existing_local_image_without_refresh(monkeypatch) -> None:
    monkeypatch.setattr(mcp_server.settings, "_data", {})
    monkeypatch.setattr(
        mcp_server.settings,
        "set",
        lambda key, value: mcp_server.settings._data.__setitem__(key, value),
    )

    class DummyDockerRuntime:
        def image_exists(self, image):
            return image == "unifem/calculix-desktop:latest"

        def pull_image(self, image, *, timeout=3600, use_default_config=False):
            raise AssertionError("pull_image should be skipped for existing local image")

    monkeypatch.setattr("cae.mcp_server.DockerRuntime", DummyDockerRuntime)

    payload = tool_docker_pull(image="calculix", timeout=12, set_default=True)

    assert payload["ok"] is True
    assert payload["data"]["skipped_pull"] is True
    assert payload["data"]["default_saved"] is True
    assert mcp_server.settings._data["docker_calculix_image"] == "unifem/calculix-desktop:latest"


def test_tool_docker_pull_saves_default_by_solver_family(monkeypatch) -> None:
    monkeypatch.setattr(mcp_server.settings, "_data", {})
    monkeypatch.setattr(
        mcp_server.settings,
        "set",
        lambda key, value: mcp_server.settings._data.__setitem__(key, value),
    )

    class DummyDockerRuntime:
        def image_exists(self, image):
            return image == "simvia/code_aster:stable"

        def pull_image(self, image, *, timeout=3600, use_default_config=False):
            raise AssertionError("pull_image should be skipped for existing local image")

    monkeypatch.setattr("cae.mcp_server.DockerRuntime", DummyDockerRuntime)

    payload = tool_docker_pull(image="code-aster", timeout=12, set_default=True)

    assert payload["ok"] is True
    assert payload["data"]["default_key"] == "docker_code_aster_image"
    assert mcp_server.settings._data["docker_code_aster_image"] == "simvia/code_aster:stable"


def test_tool_docker_run_uses_generic_runner(monkeypatch, workspace: Path) -> None:
    cfg = workspace / "case.cfg"
    cfg.write_text("SOLVER=EULER\n", encoding="utf-8")
    out_dir = workspace / "out"

    class DummyDockerRunner:
        def run(self, image, input_path, output_dir, **kwargs):
            assert image == "su2"
            assert input_path == cfg.resolve()
            assert output_dir == out_dir.resolve()
            assert kwargs["command"] == "SU2_CFD case.cfg"
            return DockerSolverRunResult(
                success=True,
                solver="su2",
                image="ghcr.io/su2code/su2/build-su2:250717-1402",
                input_path=cfg,
                output_dir=out_dir,
                command=["SU2_CFD", "case.cfg"],
                output_files=[out_dir / "history.csv"],
                stdout="done",
                stderr="",
                returncode=0,
                duration_seconds=0.2,
            )

    monkeypatch.setattr("cae.mcp_server.DockerSolverRunner", DummyDockerRunner)

    payload = tool_docker_run(
        image="su2",
        input_path=str(cfg),
        output_dir=str(out_dir),
        command="SU2_CFD case.cfg",
    )

    assert payload["ok"] is True
    assert payload["data"]["solver"] == "su2"


def test_tool_docker_build_su2_runtime_sets_default(monkeypatch) -> None:
    monkeypatch.setattr(mcp_server.settings, "_data", {})
    monkeypatch.setattr(
        mcp_server.settings,
        "set",
        lambda key, value: mcp_server.settings._data.__setitem__(key, value),
    )

    class DummyDockerRuntime:
        def build_image(self, *, context_dir, dockerfile, tag, build_args, timeout, pull):
            assert dockerfile.name == "su2-runtime-conda.Dockerfile"
            assert tag == "local/su2-runtime:test"
            assert build_args["SU2_VERSION"] == "8.3.0"
            assert pull is False
            return ContainerRunResult(
                stdout="built",
                stderr="",
                returncode=0,
                duration_seconds=0.1,
                command=["docker", "build"],
            )

    monkeypatch.setattr("cae.mcp_server.DockerRuntime", DummyDockerRuntime)

    payload = tool_docker_build_su2_runtime(
        tag="local/su2-runtime:test",
        pull_base=False,
    )

    assert payload["ok"] is True
    assert payload["data"]["default_saved"] is True
    assert mcp_server.settings._data["docker_su2_image"] == "local/su2-runtime:test"


def test_tool_docker_calculix_is_separate_from_native_solve(monkeypatch, workspace: Path) -> None:
    inp = workspace / "model.inp"
    inp.write_text("*NODE\n1,0,0,0\n", encoding="utf-8")
    out_dir = workspace / "docker_results"
    frd = out_dir / "model.frd"

    class DummyDockerRunner:
        def run(self, inp_file, output_dir, *, image=None, timeout=3600, cpus=None, memory=None):
            output_dir.mkdir(parents=True, exist_ok=True)
            frd.write_text("dummy", encoding="utf-8")
            return SolveResult(
                success=True,
                output_dir=output_dir,
                output_files=[frd],
                stdout="docker ok",
                stderr="",
                returncode=0,
                duration_seconds=0.3,
            )

    monkeypatch.setattr("cae.mcp_server.CalculixDockerRunner", DummyDockerRunner)

    payload = tool_docker_calculix(
        inp_file=str(inp),
        output_dir=str(out_dir),
        image="calculix:test",
        timeout=10,
    )

    assert payload["ok"] is True
    assert payload["data"]["success"] is True
    assert payload["data"]["frd_file"] is not None


def test_tool_diagnose_returns_json_payload(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.diagnose_results",
        lambda *args, **kwargs: DiagnoseResult(success=True),
    )
    monkeypatch.setattr(
        "cae.mcp_server.diagnosis_result_to_dict",
        lambda result, **kwargs: {
            "success": True,
            "issue_count": 0,
            "issues": [],
            "summary": {"total": 0, "execution_plan": []},
            "convergence": {"summary": {"file_count": 0}, "files": []},
            "solver_run": {
                "solver": "unknown",
                "status": "unknown",
                "status_reason": None,
                "primary_log": None,
                "text_sources": [],
                "artifacts": {
                    "input_files": [],
                    "log_files": [],
                    "result_files": [],
                },
            },
            "meta": {"results_dir": str(results_dir), "detected_solver": "unknown", "solver_status": "unknown"},
        },
    )

    payload = tool_diagnose(results_dir=str(results_dir))

    assert payload["ok"] is True
    assert payload["data"]["success"] is True
    assert payload["data"]["issue_count"] == 0
    assert payload["data"]["agent"]["solver_status_gate"]["route"] == "evidence_expansion"
    assert payload["data"]["agent"]["selected_route_context"]["action_kind"] == "evidence_collection_plan"
    assert payload["data"]["agent"]["selected_route_execution"]["available"] is False
    assert payload["data"]["agent"]["selected_route_execution"]["write_readiness"] == "no_execution_plan"
    assert (
        payload["data"]["agent"]["selected_route_handoff"]["preferred_agent_branch"]
        == "continue_route_analysis"
    )
    assert payload["data"]["agent"]["post_route_step"]["kind"] == "route_post_action"
    assert payload["data"]["agent"]["post_route_step"]["branch"] == "continue_route_analysis"
    assert (
        payload["data"]["agent"]["recommended_post_route_action"]
        == "Continue evidence collection for the selected route."
    )
    assert payload["data"]["routing"]["route"] == "evidence_expansion"
    assert payload["data"]["routing"]["decision_source"] == "solver_status_gate"
    assert payload["data"]["routing"]["action_context"]["action_kind"] == "evidence_collection_plan"
    assert payload["data"]["routing"]["selected_route_handoff"]["write_readiness"] == "no_execution_plan"
    assert payload["data"]["meta"]["routing_route"] == "evidence_expansion"
    assert payload["data"]["routing"]["followup"]["focus"] == "evidence"
    assert payload["data"]["routing"]["followup"]["handoff"]["needs_more_evidence"] is True
    assert "primary_log" in payload["data"]["routing"]["followup"]["classification_gaps"]
    assert payload["data"]["routing"]["followup"]["evidence_status"]["has_primary_log"] is False
    assert (
        payload["data"]["agent"]["recommended_next_action"]
        == "Inspect logs and artifacts to classify solver status before auto-fix or physics diagnosis."
    )


def test_tool_diagnose_ai_uses_resolved_model_name(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    captured: dict[str, str] = {}

    class DummyClient:
        def __init__(self, config):
            captured["model_name"] = config.model_name

    monkeypatch.setattr(
        "cae.ai.llm_client.resolve_ollama_model_name_with_source",
        lambda model_name=None: (model_name or "cae-ft:v1", "explicit" if model_name else "default"),
    )
    monkeypatch.setattr("cae.ai.llm_client.LLMClient", DummyClient)
    monkeypatch.setattr(
        "cae.mcp_server.diagnose_results",
        lambda *args, **kwargs: DiagnoseResult(success=True),
    )
    monkeypatch.setattr(
        "cae.mcp_server.diagnosis_result_to_dict",
        lambda result, **kwargs: {
            "success": True,
            "issue_count": 0,
            "issues": [],
            "summary": {"total": 0, "execution_plan": []},
            "convergence": {"summary": {"file_count": 0}, "files": []},
            "solver_run": {
                "solver": "unknown",
                "status": "unknown",
                "status_reason": None,
                "primary_log": None,
                "text_sources": [],
                "artifacts": {
                    "input_files": [],
                    "log_files": [],
                    "result_files": [],
                },
            },
            "meta": {"results_dir": str(results_dir), "detected_solver": "unknown", "solver_status": "unknown"},
        },
    )

    payload = tool_diagnose(results_dir=str(results_dir), ai=True)

    assert payload["ok"] is True
    assert captured["model_name"] == "cae-ft:v1"
    assert payload["data"]["meta"]["resolved_model_name"] == "cae-ft:v1"
    assert payload["data"]["meta"]["model_resolution_source"] == "default"


def test_tool_diagnose_normalizes_uppercase_solver_status_for_routing(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.diagnose_results",
        lambda *args, **kwargs: DiagnoseResult(success=False),
    )
    monkeypatch.setattr(
        "cae.mcp_server.diagnosis_result_to_dict",
        lambda result, **kwargs: {
            "success": False,
            "issue_count": 1,
            "issues": [],
            "summary": {"total": 1, "execution_plan": []},
            "convergence": {"summary": {"file_count": 0}, "files": []},
            "solver_run": {
                "solver": "openfoam",
                "status": "FAILED",
                "status_reason": "FOAM FATAL ERROR: patch field missing",
                "primary_log": "logs\\docker-openfoam.log",
                "text_sources": [{"path": "logs\\docker-openfoam.log", "kind": "runtime_log"}],
                "artifacts": {
                    "input_files": ["system\\controlDict"],
                    "log_files": ["logs\\docker-openfoam.log"],
                    "result_files": [],
                },
            },
            "meta": {"results_dir": str(results_dir), "detected_solver": "openfoam", "solver_status": "FAILED"},
        },
    )

    payload = tool_diagnose(results_dir=str(results_dir))

    assert payload["ok"] is True
    assert payload["data"]["agent"]["solver_run"]["status"] == "failed"
    assert payload["data"]["agent"]["solver_status_gate"]["route"] == "runtime_remediation"
    assert payload["data"]["routing"]["route"] == "runtime_remediation"


def test_tool_diagnose_exposes_solver_run_artifact_previews(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.diagnose_results",
        lambda *args, **kwargs: DiagnoseResult(success=False),
    )
    monkeypatch.setattr(
        "cae.mcp_server.diagnosis_result_to_dict",
        lambda result, **kwargs: {
            "success": False,
            "issue_count": 1,
            "issues": [],
            "summary": {"total": 1, "execution_plan": []},
            "convergence": {"summary": {"file_count": 0}, "files": []},
            "solver_run": {
                "solver": "openfoam",
                "status": "failed",
                "status_reason": "FOAM FATAL ERROR: patch field missing",
                "primary_log": "logs\\docker-openfoam.log",
                "text_sources": [
                    {"path": "logs\\docker-openfoam.log", "kind": "runtime_log"},
                    {"path": "logs\\docker-openfoam.log", "kind": "runtime_log"},
                    {"path": "logs\\solver.err", "kind": "runtime_log"},
                    "misc\\notes.txt",
                ],
                "artifacts": {
                    "input_files": ["system\\controlDict", "system\\fvSchemes"],
                    "log_files": ["logs\\docker-openfoam.log", "logs\\docker-openfoam.log"],
                    "result_files": ["post\\U.vtk", "post\\p.vtk"],
                },
            },
            "meta": {"results_dir": str(results_dir), "detected_solver": "openfoam", "solver_status": "failed"},
        },
    )

    payload = tool_diagnose(results_dir=str(results_dir))

    assert payload["ok"] is True
    agent_solver_run = payload["data"]["agent"]["solver_run"]
    assert agent_solver_run["primary_log"] == "logs/docker-openfoam.log"
    assert agent_solver_run["has_primary_log"] is True
    assert agent_solver_run["log_files"] == ["logs/docker-openfoam.log"]
    assert agent_solver_run["input_files"] == ["system/controlDict", "system/fvSchemes"]
    assert agent_solver_run["result_files"] == ["post/U.vtk", "post/p.vtk"]
    assert agent_solver_run["text_sources"][0] == {
        "path": "logs/docker-openfoam.log",
        "kind": "runtime_log",
    }

    routing = payload["data"]["routing"]
    assert routing["primary_log"] == "logs/docker-openfoam.log"
    assert routing["has_primary_log"] is True
    assert routing["log_files"] == ["logs/docker-openfoam.log"]
    assert routing["result_file_count"] == 2


def test_tool_diagnose_adds_agent_execution_context(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.diagnose_results",
        lambda *args, **kwargs: DiagnoseResult(success=True),
    )
    monkeypatch.setattr(
        "cae.mcp_server.diagnosis_result_to_dict",
        lambda result, **kwargs: {
            "success": True,
            "issue_count": 2,
            "summary": {
                "total": 2,
                "blocking_count": 1,
                "needs_review_count": 0,
                "risk_level": "high",
                "top_issue": {
                    "category": "input_syntax",
                    "severity": "error",
                    "message": "Missing *STEP block",
                    "location": "model.inp",
                    "evidence_line": "case.stderr:8: missing *STEP",
                    "triage": "safe_auto_fix",
                    "confidence": "high",
                    "auto_fixable": True,
                },
                "first_action": "Add missing *STEP block",
                "action_items": [
                    "Add missing *STEP block",
                    "Inspect boundary constraints",
                ],
                "execution_plan": [
                    {
                        "step": 1,
                        "triage": "blocking",
                        "category": "boundary_condition",
                        "severity": "error",
                        "confidence": "high",
                        "auto_fixable": False,
                        "action": "Inspect boundary constraints",
                        "evidence_line": "case.stderr:4: zero pivot",
                    },
                    {
                        "step": 2,
                        "triage": "safe_auto_fix",
                        "category": "input_syntax",
                        "severity": "error",
                        "confidence": "high",
                        "auto_fixable": True,
                        "action": "Add missing *STEP block",
                        "evidence_line": "case.stderr:8: missing *STEP",
                    },
                ],
            },
            "issues": [
                {
                    "category": "input_syntax",
                    "severity": "error",
                    "message": "Missing *STEP block",
                    "location": "model.inp",
                    "evidence_line": "case.stderr:8: missing *STEP",
                    "triage": "safe_auto_fix",
                    "confidence": "high",
                    "auto_fixable": True,
                }
            ],
            "similar_cases": [
                {
                    "name": "beam_case",
                    "similarity_score": 88.0,
                    "reason": "Similar load and support setup",
                }
            ],
            "solver_run": {
                "solver": "calculix",
                "status": "success",
                "status_reason": "CalculiX FRD result file detected.",
                "primary_log": "case.sta",
                "text_sources": [{"path": "case.sta", "kind": "sta"}],
                "artifacts": {
                    "input_files": ["model.inp"],
                    "log_files": ["docker-calculix.log"],
                    "result_files": ["model.frd"],
                },
            },
            "convergence": {
                "summary": {
                    "file_count": 1,
                    "has_not_converged": False,
                    "max_iterations": 8,
                    "worst_final_residual": 1e-5,
                    "residual_trend_counts": {"decreasing": 1},
                    "increment_trend_counts": {"shrinking": 1},
                },
                "files": [],
            },
            "meta": {
                "results_dir": str(results_dir),
                "detected_solver": "calculix",
                "solver_status": "success",
            },
        },
    )

    payload = tool_diagnose(results_dir=str(results_dir))

    assert payload["ok"] is True
    agent = payload["data"]["agent"]
    assert agent["safe_auto_fix_available"] is True
    assert agent["blocking_count"] == 1
    assert agent["risk_level"] == "high"
    assert agent["workflow_order"][0] == "solver_status_gate"
    assert agent["solver_run"]["solver"] == "calculix"
    assert agent["solver_status_gate"]["route"] == "physics_diagnosis"
    assert agent["next_step"]["triage"] == "safe_auto_fix"
    assert agent["next_step"]["source_step"] == 2
    assert agent["diagnosis_next_step"]["triage"] == "safe_auto_fix"
    assert agent["recommended_next_action"] == "Add missing *STEP block"
    assert agent["selected_route_context"]["action_kind"] == "physics_interpretation_prompt"
    assert "Interpret the current solver results" in agent["selected_route_context"]["prompt"]
    assert agent["selected_route_execution"]["available"] is False
    assert agent["selected_route_execution"]["write_readiness"] == "no_execution_plan"
    assert agent["selected_route_handoff"]["selected_execution_available"] is False
    assert agent["post_route_step"]["kind"] == "route_post_action"
    assert agent["post_route_step"]["branch"] == "continue_route_analysis"
    assert agent["recommended_post_route_action"] == agent["post_route_step"]["action"]
    routing = payload["data"]["routing"]
    assert routing["route"] == "physics_diagnosis"
    assert routing["decision_source"] == "diagnosis_plan"
    assert routing["selected_next_step"]["triage"] == "safe_auto_fix"
    assert routing["diagnosis_next_step"]["triage"] == "safe_auto_fix"
    assert routing["action_context"]["action_kind"] == "physics_interpretation_prompt"
    assert routing["followup"]["focus"] == "physics"
    assert routing["followup"]["handoff"]["ready_for_physics_diagnosis"] is True
    assert routing["followup"]["artifact_snapshot"]["result_file_count"] == 1
    assert routing["followup"]["result_readiness"]["ready_for_interpretation"] is True
    assert routing["followup"]["first_action"] == "Add missing *STEP block"
    assert routing["followup"]["action_items"][0] == "Add missing *STEP block"
    assert routing["followup"]["similar_cases"][0]["name"] == "beam_case"
    assert payload["data"]["meta"]["routing_decision_source"] == "diagnosis_plan"


def test_tool_diagnose_routes_failed_solver_before_diagnosis_plan(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.diagnose_results",
        lambda *args, **kwargs: DiagnoseResult(success=False),
    )
    monkeypatch.setattr(
        "cae.mcp_server.diagnosis_result_to_dict",
        lambda result, **kwargs: {
            "success": False,
            "issue_count": 1,
            "summary": {
                "total": 1,
                "blocking_count": 1,
                "needs_review_count": 0,
                "risk_level": "high",
                "execution_plan": [
                    {
                        "step": 1,
                        "triage": "safe_auto_fix",
                        "category": "input_syntax",
                        "severity": "error",
                        "confidence": "high",
                        "auto_fixable": True,
                        "action": "Patch the input file",
                    }
                ],
            },
            "issues": [
                {
                    "category": "solver_runtime",
                    "severity": "error",
                    "message": "OpenFOAM failed before completion",
                    "location": "docker-openfoam.log",
                    "evidence_line": "FOAM FATAL ERROR: cannot find patch field",
                    "triage": "blocking",
                    "confidence": "high",
                    "auto_fixable": False,
                }
            ],
            "solver_run": {
                "solver": "openfoam",
                "status": "failed",
                "status_reason": "FOAM FATAL ERROR: cannot find patch field",
                "primary_log": "docker-openfoam.log",
                "text_sources": [{"path": "docker-openfoam.log", "kind": "docker_log"}],
                "artifacts": {
                    "input_files": ["case.foam"],
                    "log_files": ["docker-openfoam.log"],
                    "result_files": [],
                },
            },
            "meta": {
                "results_dir": str(results_dir),
                "detected_solver": "openfoam",
                "solver_status": "failed",
            },
        },
    )

    payload = tool_diagnose(results_dir=str(results_dir))

    assert payload["ok"] is True
    agent = payload["data"]["agent"]
    assert agent["solver_status_gate"]["route"] == "runtime_remediation"
    assert agent["gate_overrides_diagnosis_plan"] is True
    assert agent["next_step"]["kind"] == "solver_status_route"
    assert agent["next_step"]["route"] == "runtime_remediation"
    assert "physics_diagnosis" in agent["solver_status_gate"]["blocked_actions"]
    assert agent["diagnosis_next_step"]["triage"] == "safe_auto_fix"
    assert (
        agent["recommended_next_action"]
        == "Inspect the solver runtime failure before attempting physics diagnosis."
    )
    assert agent["selected_route_context"]["action_kind"] == "runtime_remediation_prompt"
    assert "Prioritize OpenFOAM case-tree consistency" in agent["selected_route_context"]["prompt"]
    assert "Solver-run evidence preview:" in agent["selected_route_context"]["prompt"]
    assert "Solver-run branch:" in agent["selected_route_context"]["prompt"]
    assert agent["selected_route_context"]["solver_run"]["primary_log"] == "docker-openfoam.log"
    assert agent["selected_route_context"]["solver_run"]["input_files"] == ["case.foam"]
    assert agent["selected_route_context"]["solver_run_branch"]["branch"] == "openfoam_case_repair"
    assert any(
        item["target_id"] == "openfoam_case_tree"
        for item in agent["selected_route_context"]["remediation_targets"]
    )
    assert any(
        scope["path_hint"] == "constant/polyMesh/boundary"
        for scope in agent["selected_route_context"]["bounded_edit_scopes"]
    )
    assert any(
        scope["write_policy"] == "runtime_input_reconcile"
        for scope in agent["selected_route_context"]["bounded_edit_scopes"]
    )
    assert any(
        candidate["proposed_action"] == "restore_case_layout"
        for candidate in agent["selected_route_context"]["controlled_edit_candidates"]
    )
    assert any(
        payload["executor_kind"] == "runtime_input_patch"
        for payload in agent["selected_route_context"]["edit_payload_templates"]
    )
    assert any(
        plan["preview_only"] is True and plan["executor_kind"] == "runtime_input_patch"
        for plan in agent["selected_route_context"]["edit_execution_plans"]
    )
    assert agent["selected_route_execution"]["available"] is True
    assert agent["selected_route_execution"]["selection_kind"] == "execution_plan"
    assert (
        agent["selected_route_execution"]["selected_payload_id"]
        == "payload:runtime:openfoam_case_tree:openfoam_case_layout:restore_case_layout"
    )
    assert "openfoam_case_repair" in agent["selected_route_execution"]["selection_reason"]
    assert (
        agent["selected_route_execution"]["branch_score_breakdown"]["branch"]
        == "openfoam_case_repair"
    )
    assert any(
        item["term"] == "restore_case_layout"
        for item in agent["selected_route_execution"]["branch_score_breakdown"]["matched_branch_terms"]
    )
    assert agent["selected_route_execution"]["write_readiness"] == "ready_for_write_guard"
    assert agent["selected_route_execution"]["status_flags"]["ready_for_write_guard"] is True
    assert (
        agent["selected_route_execution"]["dry_run_validation"]["status"]
        == "ready_for_write_guard"
    )
    assert agent["selected_route_handoff"]["preferred_agent_branch"] == "guarded_write_candidate"
    assert agent["selected_route_handoff"]["solver_run_branch"]["branch"] == "openfoam_case_repair"
    assert "restore_case_layout" in agent["selected_route_handoff"]["selection_reason"]
    assert agent["post_route_step"]["kind"] == "route_post_action"
    assert agent["post_route_step"]["branch"] == "guarded_write_candidate"
    assert agent["post_route_step"]["solver_run_branch"]["branch"] == "openfoam_case_repair"
    assert agent["post_route_step"]["branch_score_breakdown"]["branch"] == "openfoam_case_repair"
    assert agent["post_route_step"]["details"]["verified_target_files"]
    assert agent["recommended_post_route_action"] == agent["post_route_step"]["action"]
    routing = payload["data"]["routing"]
    assert routing["route"] == "runtime_remediation"
    assert routing["decision_source"] == "solver_status_gate"
    assert routing["selected_next_step"]["route"] == "runtime_remediation"
    assert routing["action_context"]["action_kind"] == "runtime_remediation_prompt"
    assert routing["action_context"]["solver_run"]["primary_log"] == "docker-openfoam.log"
    assert routing["action_context"]["solver_run"]["log_files"] == ["docker-openfoam.log"]
    assert routing["action_context"]["solver_run_branch"]["branch"] == "openfoam_case_repair"
    assert any(
        item["target_id"] == "sidecar_input_bundle"
        for item in routing["action_context"]["remediation_targets"]
    )
    assert any(
        scope["path_hint"] == "mounted case directory"
        for scope in routing["action_context"]["bounded_edit_scopes"]
    )
    assert routing["action_context"]["write_policy_summary"]["proposal_ready_count"] >= 1
    assert routing["action_context"]["edit_payload_templates"]
    assert routing["action_context"]["edit_execution_plans"]
    assert routing["selected_route_handoff"]["write_readiness"] == "ready_for_write_guard"
    assert routing["post_route_step"]["branch"] == "guarded_write_candidate"
    assert "physics_diagnosis" in routing["blocked_actions"]
    assert routing["followup"]["focus"] == "runtime"
    assert routing["followup"]["handoff"]["needs_runtime_fix_first"] is True
    assert routing["followup"]["artifact_snapshot"]["primary_log"] == "docker-openfoam.log"
    assert routing["followup"]["priority_issues"][0]["category"] == "solver_runtime"


def test_tool_diagnose_routes_not_converged_solver_to_convergence_tuning(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.diagnose_results",
        lambda *args, **kwargs: DiagnoseResult(success=True),
    )
    monkeypatch.setattr(
        "cae.mcp_server.diagnosis_result_to_dict",
        lambda result, **kwargs: {
            "success": True,
            "issue_count": 1,
            "summary": {
                "total": 1,
                "blocking_count": 0,
                "needs_review_count": 1,
                "risk_level": "medium",
                "execution_plan": [],
            },
            "issues": [
                {
                    "category": "convergence",
                    "severity": "warning",
                    "message": "Solver reached the iteration limit before convergence.",
                    "location": "history.csv",
                    "evidence_line": "docker-su2.log: Maximum number of iterations reached",
                    "triage": "review",
                    "confidence": "medium",
                    "auto_fixable": False,
                }
            ],
            "solver_run": {
                "solver": "su2",
                "status": "not_converged",
                "status_reason": "Solver stopped after max iterations with high residuals.",
                "primary_log": "history.csv",
                "text_sources": [{"path": "history.csv", "kind": "history_csv"}],
                "artifacts": {
                    "input_files": ["inv_channel_smoke.cfg"],
                    "log_files": ["docker-su2.log"],
                    "result_files": ["history.csv"],
                },
            },
            "convergence": {
                "summary": {
                    "file_count": 1,
                    "has_not_converged": True,
                    "max_iterations": 50,
                    "worst_final_residual": 0.0012,
                    "residual_trend_counts": {"improving": 1},
                    "increment_trend_counts": {},
                },
                "files": [],
            },
            "meta": {
                "results_dir": str(results_dir),
                "detected_solver": "su2",
                "solver_status": "not_converged",
            },
        },
    )

    payload = tool_diagnose(results_dir=str(results_dir))

    assert payload["ok"] is True
    agent = payload["data"]["agent"]
    assert agent["solver_status_gate"]["route"] == "convergence_tuning"
    assert agent["gate_overrides_diagnosis_plan"] is True
    assert agent["next_step"]["kind"] == "solver_status_route"
    assert agent["next_step"]["route"] == "convergence_tuning"
    assert agent["solver_run"]["status"] == "not_converged"
    assert agent["selected_route_context"]["action_kind"] == "convergence_tuning_prompt"
    assert "Prefer SU2 controls such as CFL growth" in agent["selected_route_context"]["prompt"]
    assert "Solver-run evidence preview:" in agent["selected_route_context"]["prompt"]
    assert "Solver-run branch:" in agent["selected_route_context"]["prompt"]
    assert agent["selected_route_context"]["solver_run"]["input_files"] == ["inv_channel_smoke.cfg"]
    assert agent["selected_route_context"]["solver_run"]["result_files"] == ["history.csv"]
    assert agent["selected_route_context"]["solver_run_branch"]["branch"] == "su2_cfl_iteration_tuning"
    assert any(
        item["target_id"] == "cfl_or_time_step"
        for item in agent["selected_route_context"]["edit_targets"]
    )
    assert any(
        scope["path_hint"] == "primary SU2 cfg" and "CFL_NUMBER" in scope["block_hints"]
        for scope in agent["selected_route_context"]["bounded_edit_scopes"]
    )
    assert any(
        scope["write_policy"] == "bounded_numeric_tuning"
        for scope in agent["selected_route_context"]["bounded_edit_scopes"]
    )
    assert any(
        candidate["proposed_action"] == "decrease_cfl_growth"
        for candidate in agent["selected_route_context"]["controlled_edit_candidates"]
    )
    assert any(
        payload["executor_kind"] == "bounded_numeric_parameter_update"
        for payload in agent["selected_route_context"]["edit_payload_templates"]
    )
    assert any(
        plan["preview_only"] is True and plan["executor_kind"] == "bounded_numeric_parameter_update"
        for plan in agent["selected_route_context"]["edit_execution_plans"]
    )
    assert agent["selected_route_execution"]["available"] is True
    assert agent["selected_route_execution"]["selection_kind"] == "execution_plan"
    assert (
        agent["selected_route_execution"]["selected_payload_id"]
        == "payload:convergence:cfl_or_time_step:su2_cfl_controls:decrease_cfl_growth"
    )
    assert "su2_cfl_iteration_tuning" in agent["selected_route_execution"]["selection_reason"]
    assert any(
        item["term"] == "decrease_cfl_growth"
        for item in agent["selected_route_execution"]["branch_score_breakdown"]["matched_branch_terms"]
    )
    assert agent["selected_route_execution"]["write_readiness"] == "needs_path_resolution"
    assert agent["selected_route_execution"]["status_flags"]["needs_path_resolution"] is True
    assert (
        agent["selected_route_execution"]["dry_run_validation"]["status"]
        == "needs_path_resolution"
    )
    assert agent["selected_route_handoff"]["preferred_agent_branch"] == "resolve_declared_targets"
    assert agent["selected_route_handoff"]["solver_run_branch"]["branch"] == "su2_cfl_iteration_tuning"
    assert "decrease_cfl_growth" in agent["selected_route_handoff"]["selection_reason"]
    assert agent["post_route_step"]["kind"] == "route_post_action"
    assert agent["post_route_step"]["branch"] == "resolve_declared_targets"
    assert agent["post_route_step"]["solver_run_branch"]["branch"] == "su2_cfl_iteration_tuning"
    assert agent["post_route_step"]["branch_score_breakdown"]["branch"] == "su2_cfl_iteration_tuning"
    assert (
        agent["post_route_step"]["details"]["unresolved_targets"]
        == ["<primary_su2_cfg>"]
    )
    assert agent["recommended_post_route_action"] == agent["post_route_step"]["action"]
    routing = payload["data"]["routing"]
    assert routing["route"] == "convergence_tuning"
    assert routing["decision_source"] == "solver_status_gate"
    assert routing["selected_next_step"]["route"] == "convergence_tuning"
    assert routing["action_context"]["action_kind"] == "convergence_tuning_prompt"
    assert routing["action_context"]["solver_run"]["primary_log"] == "history.csv"
    assert routing["action_context"]["solver_run"]["log_files"] == ["docker-su2.log"]
    assert routing["action_context"]["solver_run_branch"]["branch"] == "su2_cfl_iteration_tuning"
    assert any(
        item["target_id"] == "iteration_budget"
        for item in routing["action_context"]["edit_targets"]
    )
    assert any(
        scope["path_hint"] == "primary SU2 cfg" and "EXT_ITER" in scope["block_hints"]
        for scope in routing["action_context"]["bounded_edit_scopes"]
    )
    assert routing["action_context"]["write_policy_summary"]["proposal_ready_count"] >= 1
    assert routing["action_context"]["edit_payload_templates"]
    assert routing["action_context"]["edit_execution_plans"]
    assert routing["selected_route_handoff"]["write_readiness"] == "needs_path_resolution"
    assert routing["post_route_step"]["branch"] == "resolve_declared_targets"
    assert routing["followup"]["focus"] == "convergence"
    assert routing["followup"]["convergence_summary"]["max_iterations"] == 50
    assert routing["followup"]["handoff"]["needs_convergence_tuning_first"] is True
    assert routing["followup"]["tuning_hints"]
    assert (
        agent["recommended_next_action"]
        == "Tune convergence controls before treating the current result as a valid physics answer."
    )


def test_tool_diagnose_exposes_guarded_write_candidate_post_route_step(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = results_dir / "inv_channel_smoke.cfg"
    cfg_file.write_text(
        "EXT_ITER=50\nCFL_NUMBER=1.5\nLINEAR_SOLVER_ERROR=1E-6\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server.diagnose_results",
        lambda *args, **kwargs: DiagnoseResult(success=True),
    )
    monkeypatch.setattr(
        "cae.mcp_server.diagnosis_result_to_dict",
        lambda result, **kwargs: {
            "success": True,
            "issue_count": 1,
            "summary": {
                "total": 1,
                "blocking_count": 0,
                "needs_review_count": 1,
                "risk_level": "medium",
                "execution_plan": [],
            },
            "issues": [
                {
                    "category": "convergence",
                    "severity": "warning",
                    "message": "Solver reached the iteration limit before convergence.",
                    "location": "history.csv",
                    "evidence_line": "docker-su2.log: Maximum number of iterations reached",
                    "triage": "review",
                    "confidence": "medium",
                    "auto_fixable": False,
                }
            ],
            "solver_run": {
                "solver": "su2",
                "status": "not_converged",
                "status_reason": "Solver stopped after max iterations with high residuals.",
                "primary_log": "history.csv",
                "text_sources": [{"path": "history.csv", "kind": "history_csv"}],
                "artifacts": {
                    "input_files": ["inv_channel_smoke.cfg"],
                    "log_files": ["docker-su2.log"],
                    "result_files": ["history.csv"],
                },
            },
            "convergence": {
                "summary": {
                    "file_count": 1,
                    "has_not_converged": True,
                    "max_iterations": 50,
                    "worst_final_residual": 0.0012,
                    "residual_trend_counts": {"improving": 1},
                    "increment_trend_counts": {},
                },
                "files": [],
            },
            "meta": {
                "results_dir": str(results_dir),
                "detected_solver": "su2",
                "solver_status": "not_converged",
            },
        },
    )

    payload = tool_diagnose(results_dir=str(results_dir))

    assert payload["ok"] is True
    agent = payload["data"]["agent"]
    assert agent["selected_route_execution"]["write_readiness"] == "ready_for_write_guard"
    assert agent["selected_route_execution"]["write_guard_passed"] is True
    assert (
        agent["selected_route_execution"]["selected_payload_id"]
        == "payload:convergence:cfl_or_time_step:su2_cfl_controls:decrease_cfl_growth"
    )
    assert "cfl_number" in agent["selected_route_execution"]["selection_reason"]
    assert agent["selected_route_handoff"]["preferred_agent_branch"] == "guarded_write_candidate"
    assert agent["post_route_step"]["branch"] == "guarded_write_candidate"
    assert agent["post_route_step"]["write_guard_passed"] is True
    assert agent["post_route_step"]["details"]["verified_target_files"] == [str(cfg_file)]
    assert (
        agent["recommended_post_route_action"]
        == "Advance the selected preview plan into the guarded write executor."
    )
    routing = payload["data"]["routing"]
    assert routing["post_route_step"]["branch"] == "guarded_write_candidate"
    assert routing["selected_route_handoff"]["write_readiness"] == "ready_for_write_guard"


def test_tool_diagnose_wraps_diagnosis_exceptions(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    def fail(*args, **kwargs):
        raise RuntimeError("diagnosis crashed")

    monkeypatch.setattr("cae.mcp_server.diagnose_results", fail)

    payload = tool_diagnose(results_dir=str(results_dir))

    assert payload["ok"] is False
    assert payload["error"]["code"] == "diagnose_failed"
    assert "diagnosis crashed" in payload["error"]["message"]


def test_tool_runtime_remediation_returns_followup_for_failed_route(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                    },
                },
            },
            None,
        ),
    )

    payload = tool_runtime_remediation(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["applicable"] is True
    assert data["expected_route"] == "runtime_remediation"
    assert data["actual_route"] == "runtime_remediation"
    assert data["followup"]["focus"] == "runtime"
    assert data["summary"]["risk_level"] == "high"


def test_tool_runtime_remediation_reports_route_mismatch(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 2,
                "summary": {"risk_level": "medium"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "calculix",
                    "solver_status": "success",
                },
                "routing": {
                    "route": "physics_diagnosis",
                    "decision_source": "diagnosis_plan",
                    "recommended_next_action": "Add missing *STEP block",
                    "blocked_actions": [],
                    "followup": {
                        "focus": "physics",
                        "handoff": {"ready_for_physics_diagnosis": True},
                    },
                },
            },
            None,
        ),
    )

    payload = tool_runtime_remediation(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["applicable"] is False
    assert data["actual_route"] == "physics_diagnosis"
    assert "not 'runtime_remediation'" in data["message"]
    assert data["followup"]["focus"] == "physics"


def test_tool_convergence_tuning_returns_followup_for_not_converged_route(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "medium"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "su2",
                    "solver_status": "not_converged",
                },
                "routing": {
                    "route": "convergence_tuning",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Tune convergence controls before treating the current result as a valid physics answer.",
                    "blocked_actions": ["physics_diagnosis_as_final_answer"],
                    "followup": {
                        "focus": "convergence",
                        "handoff": {"needs_convergence_tuning_first": True},
                        "convergence_summary": {"max_iterations": 50},
                    },
                },
            },
            None,
        ),
    )

    payload = tool_convergence_tuning(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["applicable"] is True
    assert data["actual_route"] == "convergence_tuning"
    assert data["followup"]["focus"] == "convergence"
    assert data["followup"]["convergence_summary"]["max_iterations"] == 50


def test_tool_physics_diagnosis_returns_followup_for_success_route(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 2,
                "summary": {"risk_level": "medium"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "calculix",
                    "solver_status": "success",
                },
                "routing": {
                    "route": "physics_diagnosis",
                    "decision_source": "diagnosis_plan",
                    "recommended_next_action": "Inspect boundary constraints",
                    "blocked_actions": [],
                    "followup": {
                        "focus": "physics",
                        "handoff": {"ready_for_physics_diagnosis": True},
                        "result_readiness": {"ready_for_interpretation": True},
                    },
                },
            },
            None,
        ),
    )

    payload = tool_physics_diagnosis(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["applicable"] is True
    assert data["actual_route"] == "physics_diagnosis"
    assert data["followup"]["focus"] == "physics"
    assert data["followup"]["result_readiness"]["ready_for_interpretation"] is True


def test_tool_evidence_expansion_returns_followup_for_unknown_route(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 0,
                "summary": {"risk_level": "low"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "unknown",
                    "solver_status": "unknown",
                },
                "routing": {
                    "route": "evidence_expansion",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect logs and artifacts to classify solver status before auto-fix or physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "evidence",
                        "handoff": {"needs_more_evidence": True},
                        "classification_gaps": ["primary_log", "text_sources"],
                    },
                },
            },
            None,
        ),
    )

    payload = tool_evidence_expansion(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["applicable"] is True
    assert data["actual_route"] == "evidence_expansion"
    assert data["followup"]["focus"] == "evidence"
    assert "primary_log" in data["followup"]["classification_gaps"]


def test_tool_runtime_retry_checks_builds_runtime_action_payload(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_runtime_remediation",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "runtime_remediation",
                "actual_route": "runtime_remediation",
                "decision_source": "solver_status_gate",
                "solver": "openfoam",
                "solver_status": "failed",
                "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                "summary": {"risk_level": "high"},
                "followup": {
                    "checklist": [{"check": "image", "instruction": "Confirm the selected solver image exists locally."}],
                    "artifact_snapshot": {
                        "primary_log": "docker-openfoam.log",
                        "status_reason": "FOAM FATAL ERROR: cannot find patch field",
                        "log_files": ["docker-openfoam.log"],
                    },
                    "priority_issues": [{"category": "solver_runtime"}],
                },
            },
        },
    )

    payload = tool_runtime_retry_checks(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["action_kind"] == "runtime_retry_checks"
    assert data["retry_ready"] is True
    assert data["pre_retry_checks"][0]["check"] == "image"
    assert data["blocking_signals"]["primary_log"] == "docker-openfoam.log"
    assert any(item["area"] == "docker_image_reference" for item in data["docker_runtime_checks"])
    assert any(item["area"] == "container_sidecar_inputs" for item in data["docker_runtime_checks"])
    assert any(item["area"] == "openfoam_boundary_fields" for item in data["solver_specific_checks"])
    assert any(item["mode"] == "openfoam_case_structure_mismatch" for item in data["suspected_failure_modes"])


def test_tool_convergence_parameter_suggestions_builds_deterministic_suggestions(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_convergence_tuning",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "convergence_tuning",
                "actual_route": "convergence_tuning",
                "decision_source": "solver_status_gate",
                "solver": "su2",
                "solver_status": "not_converged",
                "recommended_next_action": "Tune convergence controls before treating the current result as a valid physics answer.",
                "summary": {"risk_level": "medium"},
                "followup": {
                    "convergence_summary": {
                        "max_iterations": 50,
                        "file_count": 1,
                        "residual_trend_counts": {"worsening": 1},
                        "worst_final_residual": 0.0012,
                    },
                    "tuning_hints": ["Review whether the solver stopped because the iteration budget was exhausted."],
                    "priority_issues": [{"category": "convergence"}],
                },
            },
        },
    )

    payload = tool_convergence_parameter_suggestions(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["action_kind"] == "convergence_parameter_suggestions"
    assert any(item["parameter_area"] == "iteration_budget" for item in data["parameter_suggestions"])
    assert any(item["parameter_area"] == "time_step_control" for item in data["parameter_suggestions"])
    assert any(item["parameter_area"] == "cfl_or_time_step" for item in data["solver_specific_suggestions"])
    assert any(item["parameter_area"] == "linear_solver" for item in data["solver_specific_suggestions"])
    assert data["tuning_hints"]


def test_tool_convergence_parameter_suggestions_adds_openfoam_specific_rules(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_convergence_tuning",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "convergence_tuning",
                "actual_route": "convergence_tuning",
                "decision_source": "solver_status_gate",
                "solver": "openfoam",
                "solver_status": "not_converged",
                "recommended_next_action": "Tune convergence controls before treating the current result as a valid physics answer.",
                "summary": {"risk_level": "medium"},
                "followup": {
                    "convergence_summary": {
                        "max_iterations": 120,
                        "file_count": 1,
                        "residual_trend_counts": {"improving": 1},
                        "worst_final_residual": 0.02,
                    },
                    "tuning_hints": ["Keep the current setup mostly intact and tune tolerances or iteration limits gradually."],
                    "priority_issues": [{"category": "convergence"}],
                },
            },
        },
    )

    payload = tool_convergence_parameter_suggestions(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert any(item["parameter_area"] == "deltaT_maxCo" for item in data["solver_specific_suggestions"])
    assert any(item["parameter_area"] == "fvSolution_relaxation" for item in data["solver_specific_suggestions"])
    assert any(item["parameter_area"] == "residual_target" for item in data["solver_specific_suggestions"])


def test_tool_runtime_retry_checks_adds_code_aster_specific_rules_and_failure_modes(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_runtime_remediation",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "runtime_remediation",
                "actual_route": "runtime_remediation",
                "decision_source": "solver_status_gate",
                "solver": "code_aster",
                "solver_status": "failed",
                "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                "summary": {"risk_level": "high"},
                "followup": {
                    "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                    "artifact_snapshot": {
                        "primary_log": "docker-code_aster.log",
                        "status_reason": "No such file or directory: case.comm",
                        "log_files": ["docker-code_aster.log"],
                    },
                    "priority_issues": [{"category": "solver_runtime", "message": "command file failed"}],
                },
            },
        },
    )

    payload = tool_runtime_retry_checks(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert any(item["area"] == "code_aster_export_sidecars" for item in data["solver_specific_checks"])
    assert any(item["area"] == "container_output_writeability" for item in data["docker_runtime_checks"])
    assert any(item["mode"] == "missing_sidecar_or_mount_path" for item in data["suspected_failure_modes"])
    assert any(item["mode"] == "code_aster_export_or_command_mismatch" for item in data["suspected_failure_modes"])


def test_tool_convergence_parameter_suggestions_adds_elmer_specific_rules(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_convergence_tuning",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "convergence_tuning",
                "actual_route": "convergence_tuning",
                "decision_source": "solver_status_gate",
                "solver": "elmer",
                "solver_status": "not_converged",
                "recommended_next_action": "Tune convergence controls before treating the current result as a valid physics answer.",
                "summary": {"risk_level": "medium"},
                "followup": {
                    "convergence_summary": {
                        "max_iterations": 30,
                        "file_count": 1,
                        "residual_trend_counts": {"improving": 1},
                        "worst_final_residual": 0.05,
                    },
                    "tuning_hints": ["Keep the current setup mostly intact and tune tolerances or iteration limits gradually."],
                    "priority_issues": [{"category": "convergence"}],
                },
            },
        },
    )

    payload = tool_convergence_parameter_suggestions(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert any(item["parameter_area"] == "linear_system_controls" for item in data["solver_specific_suggestions"])
    assert any(item["parameter_area"] == "nonlinear_system_controls" for item in data["solver_specific_suggestions"])
    assert any(item["parameter_area"] == "timestep_or_steady_controls" for item in data["solver_specific_suggestions"])
    assert any(item["parameter_area"] == "residual_target" for item in data["solver_specific_suggestions"])


def test_tool_convergence_parameter_suggestions_adds_code_aster_specific_rules(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_convergence_tuning",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "convergence_tuning",
                "actual_route": "convergence_tuning",
                "decision_source": "solver_status_gate",
                "solver": "code_aster",
                "solver_status": "not_converged",
                "recommended_next_action": "Tune convergence controls before treating the current result as a valid physics answer.",
                "summary": {"risk_level": "medium"},
                "followup": {
                    "convergence_summary": {
                        "max_iterations": 20,
                        "file_count": 1,
                        "residual_trend_counts": {"worsening": 1},
                        "worst_final_residual": 0.2,
                    },
                    "tuning_hints": ["Review whether the solver stopped because the iteration budget was exhausted."],
                    "priority_issues": [{"category": "convergence"}],
                },
            },
        },
    )

    payload = tool_convergence_parameter_suggestions(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert any(item["parameter_area"] == "newton_increment_control" for item in data["solver_specific_suggestions"])
    assert any(item["parameter_area"] == "line_search_or_contact" for item in data["solver_specific_suggestions"])
    assert any(item["parameter_area"] == "time_step_refinement" for item in data["solver_specific_suggestions"])


def test_tool_runtime_remediation_prompt_builds_solver_native_prompt(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_runtime_remediation",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "runtime_remediation",
                "actual_route": "runtime_remediation",
                "decision_source": "solver_status_gate",
                "solver": "code_aster",
                "solver_status": "failed",
                "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                "summary": {"risk_level": "high"},
                "followup": {
                    "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                    "artifact_snapshot": {
                        "primary_log": "docker-code_aster.log",
                        "status_reason": "No such file or directory: case.comm",
                        "log_files": ["docker-code_aster.log"],
                    },
                    "priority_issues": [{"category": "solver_runtime", "message": "command file failed"}],
                },
            },
        },
    )

    payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["action_kind"] == "runtime_remediation_prompt"
    assert data["agent_focus"] == "runtime_remediation"
    assert "Code_Aster `.export`/`.comm` pair" in data["prompt"]
    assert "code_aster_export_sidecars" in data["prompt"]
    assert "missing_sidecar_or_mount_path" in data["prompt"]
    assert any(item["target_id"] == "code_aster_export_bundle" for item in data["remediation_targets"])
    assert any(item["target_id"] == "code_aster_export_sidecars" for item in data["remediation_targets"])
    assert any(item["suggested_action"] == "reconcile_export_command_and_sidecars" for item in data["remediation_targets"])
    assert any(scope["path_hint"] == ".export file" for scope in data["bounded_edit_scopes"])
    assert any(
        scope["path_hint"] == ".export file" and "reconcile_export_references" in scope["allowed_actions"]
        for item in data["remediation_targets"]
        for scope in item["bounded_edit_scopes"]
    )
    assert any(
        scope["write_policy"] == "runtime_input_reconcile"
        for scope in data["bounded_edit_scopes"]
    )
    assert any(
        candidate["proposed_action"] == "copy_missing_sidecars"
        for candidate in data["controlled_edit_candidates"]
    )
    assert data["write_policy_summary"]["proposal_ready_count"] >= 1
    assert any(
        payload["executor_kind"] == "runtime_input_patch"
        and "<case>.export" in payload["target_files"]
        for payload in data["edit_payload_templates"]
    )
    assert any(
        operation["operation_kind"] == "copy_declared_sidecars"
        for payload in data["edit_payload_templates"]
        for operation in payload["operations"]
    )
    assert any(
        plan["executor_kind"] == "runtime_input_patch"
        and plan["touches_unrelated_files"] is False
        for plan in data["edit_execution_plans"]
    )
    assert any(
        artifact["artifact_kind"] == "patch_blueprint"
        for plan in data["edit_execution_plans"]
        for artifact in plan["artifacts"]
    )
    assert data["output_contract"][0] == "primary_failure_hypothesis"
    assert "remediation_targets" in data["output_contract"]
    assert "bounded_edit_scopes" in data["output_contract"]
    assert "write_policy_summary" in data["output_contract"]
    assert "controlled_edit_candidates" in data["output_contract"]
    assert "edit_payload_templates" in data["output_contract"]
    assert "edit_execution_plans" in data["output_contract"]


def test_tool_convergence_tuning_prompt_builds_solver_native_prompt(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_convergence_tuning",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "convergence_tuning",
                "actual_route": "convergence_tuning",
                "decision_source": "solver_status_gate",
                "solver": "openfoam",
                "solver_status": "not_converged",
                "recommended_next_action": "Tune convergence controls before treating the current result as a valid physics answer.",
                "summary": {"risk_level": "medium"},
                "followup": {
                    "convergence_summary": {
                        "max_iterations": 120,
                        "file_count": 1,
                        "residual_trend_counts": {"improving": 1},
                        "worst_final_residual": 0.02,
                    },
                    "tuning_hints": ["Keep the current setup mostly intact and tune tolerances or iteration limits gradually."],
                    "priority_issues": [{"category": "convergence"}],
                },
            },
        },
    )

    payload = tool_convergence_tuning_prompt(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["action_kind"] == "convergence_tuning_prompt"
    assert data["agent_focus"] == "convergence_tuning"
    assert "Prefer OpenFOAM controls such as `deltaT`, `maxCo`, `fvSolution`" in data["prompt"]
    assert "deltaT_maxCo" in data["prompt"]
    assert "fvSolution_relaxation" in data["prompt"]
    assert any(item["target_id"] == "deltaT_maxCo" for item in data["edit_targets"])
    assert any(item["target_id"] == "iteration_budget" for item in data["edit_targets"])
    assert any(item["change_strategy"] == "tune_solver_controls" for item in data["edit_targets"])
    assert any(
        scope["path_hint"] == "system/controlDict" and "deltaT" in scope["parameter_hints"]
        for scope in data["bounded_edit_scopes"]
    )
    assert any(
        scope["path_hint"] == "system/controlDict" and "decrease_deltaT" in scope["allowed_actions"]
        for item in data["edit_targets"]
        for scope in item["bounded_edit_scopes"]
    )
    assert any(
        scope["write_policy"] == "bounded_numeric_tuning"
        for scope in data["bounded_edit_scopes"]
    )
    assert any(
        candidate["proposed_action"] == "decrease_deltaT"
        for candidate in data["controlled_edit_candidates"]
    )
    assert data["write_policy_summary"]["policy_counts"]["bounded_numeric_tuning"] >= 1
    assert any(
        payload["executor_kind"] == "bounded_numeric_parameter_update"
        and "system/controlDict" in payload["target_files"]
        for payload in data["edit_payload_templates"]
    )
    assert any(
        operation["parameter"] == "deltaT" and operation["modifier"] == "decrease"
        for payload in data["edit_payload_templates"]
        for operation in payload["operations"]
    )
    assert any(
        plan["executor_kind"] == "bounded_numeric_parameter_update"
        and plan["preview_only"] is True
        for plan in data["edit_execution_plans"]
    )
    assert any(
        artifact["artifact_kind"] == "parameter_update_blueprint"
        and artifact["parameter"] == "deltaT"
        and artifact["modifier"] == "decrease"
        for plan in data["edit_execution_plans"]
        for artifact in plan["artifacts"]
    )
    assert data["convergence_summary"]["worst_final_residual"] == 0.02
    assert data["output_contract"][0] == "primary_convergence_diagnosis"
    assert "bounded_edit_scopes" in data["output_contract"]
    assert "write_policy_summary" in data["output_contract"]
    assert "controlled_edit_candidates" in data["output_contract"]
    assert "edit_payload_templates" in data["output_contract"]
    assert "edit_execution_plans" in data["output_contract"]


def test_tool_selected_edit_execution_plan_expands_runtime_payload_selection(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    export_file = results_dir / "case.export"
    export_file.write_text(
        "F comm case.comm D 1\nF mmed mesh.med D 2\nP working_dir ./\n",
        encoding="utf-8",
    )
    (results_dir / "case.comm").write_text(
        "mesh/material include references\ncommand pairing\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "code_aster",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-code_aster.log",
                            "status_reason": "No such file or directory: case.comm",
                            "log_files": ["docker-code_aster.log"],
                            "input_files": ["case.export", "case.comm"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "command file failed"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["<case>.export"]
    )

    payload = tool_selected_edit_execution_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["action_kind"] == "selected_edit_execution_plan"
    assert data["selection_kind"] == "payload_template"
    assert data["selection_found"] is True
    assert data["selected_edit_execution_plan"]["preview_only"] is True
    assert data["execution_output"]["output_kind"] == "structured_patch_plan"
    assert data["execution_output"]["patch_operations"]
    assert data["rendered_execution_preview"]["render_kind"] == "patch_text_preview"
    assert "*** Begin Preview Patch" in data["rendered_execution_preview"]["patch_text"]
    assert "*** Update File:" in data["rendered_execution_preview"]["patch_text"]
    assert "rendered_execution_preview" in data["output_contract"]
    assert "dry_run_validation" in data["output_contract"]
    assert data["dry_run_validation"]["status"] == "ready_for_write_guard"
    assert data["dry_run_validation"]["write_guard_passed"] is True
    assert data["dry_run_validation"]["target_file_checks"][0]["matched_path"] == str(export_file)
    assert data["dry_run_validation"]["selector_checks"][0]["status"] == "matched"
    assert any(
        op["patch_strategy"] == "scoped_single_surface_patch"
        for op in data["execution_output"]["patch_operations"]
    )


def test_tool_selected_edit_execution_plan_expands_convergence_plan_selection(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    system_dir = results_dir / "system"
    system_dir.mkdir(parents=True, exist_ok=True)
    control_dict = system_dir / "controlDict"
    control_dict.write_text(
        "application icoFoam;\ndeltaT 0.01;\nmaxCo 0.5;\nendTime 100;\n",
        encoding="utf-8",
    )
    (system_dir / "fvSolution").write_text(
        "solvers\n{\n    p\n    {\n        tolerance 1e-06;\n    }\n}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "medium"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "not_converged",
                },
                "routing": {
                    "route": "convergence_tuning",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Tune convergence controls before treating the current result as a valid physics answer.",
                    "blocked_actions": ["physics_diagnosis_as_final_answer"],
                    "followup": {
                        "focus": "convergence",
                        "handoff": {"needs_convergence_tuning_first": True},
                        "convergence_summary": {
                            "max_iterations": 120,
                            "file_count": 1,
                            "residual_trend_counts": {"improving": 1},
                            "worst_final_residual": 0.02,
                        },
                        "tuning_hints": ["Keep the current setup mostly intact and tune tolerances or iteration limits gradually."],
                        "priority_issues": [{"category": "convergence"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_convergence_tuning_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    plan_id = next(
        item["plan_id"]
        for item in prompt_payload["data"]["edit_execution_plans"]
        if item["target_files"] == ["system/controlDict"]
        and any(
            artifact.get("parameter") == "deltaT"
            for artifact in item.get("artifacts", [])
            if isinstance(artifact, dict)
        )
    )

    payload = tool_selected_edit_execution_plan(
        results_dir=str(results_dir),
        selection_id=plan_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["selection_kind"] == "execution_plan"
    assert data["selection_found"] is True
    assert data["execution_output"]["output_kind"] == "parameter_change_plan"
    assert data["execution_output"]["parameter_updates"]
    assert data["rendered_execution_preview"]["render_kind"] == "parameter_write_payload"
    assert data["rendered_execution_preview"]["parameter_write_payload"]["assignment_count"] >= 1
    assert "rendered_execution_preview" in data["output_contract"]
    assert "dry_run_validation" in data["output_contract"]
    assert data["dry_run_validation"]["status"] == "ready_for_write_guard"
    assert data["dry_run_validation"]["write_guard_passed"] is True
    assert data["dry_run_validation"]["target_file_checks"][0]["matched_path"] == str(control_dict)
    assert data["dry_run_validation"]["selector_checks"][0]["matched_tokens"] == ["deltaT"]
    assert any(
        update["value_policy"] == "bounded_single_adjustment"
        for update in data["execution_output"]["parameter_updates"]
    )
    assert all(
        assignment["value_expression"]
        for assignment in data["rendered_execution_preview"]["parameter_write_payload"]["assignments"]
    )


def test_tool_selected_edit_execution_plan_rejects_invalid_selection_kind(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "medium"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "not_converged",
                },
                "routing": {
                    "route": "convergence_tuning",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Tune convergence controls before treating the current result as a valid physics answer.",
                    "blocked_actions": [],
                    "followup": {
                        "focus": "convergence",
                        "handoff": {"needs_convergence_tuning_first": True},
                        "convergence_summary": {
                            "max_iterations": 120,
                            "file_count": 1,
                            "residual_trend_counts": {"improving": 1},
                            "worst_final_residual": 0.02,
                        },
                        "tuning_hints": [],
                        "priority_issues": [{"category": "convergence"}],
                    },
                },
            },
            None,
        ),
    )

    payload = tool_selected_edit_execution_plan(
        results_dir=str(results_dir),
        selection_id="payload:anything",
        selection_kind="not_valid",
    )

    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_input"


def test_tool_execute_guarded_edit_plan_applies_parameter_update(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    system_dir = results_dir / "system"
    system_dir.mkdir(parents=True, exist_ok=True)
    control_dict = system_dir / "controlDict"
    control_dict.write_text(
        "application icoFoam;\ndeltaT 0.01;\nmaxCo 0.5;\nendTime 100;\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "medium"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "not_converged",
                },
                "routing": {
                    "route": "convergence_tuning",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Tune convergence controls before treating the current result as a valid physics answer.",
                    "blocked_actions": ["physics_diagnosis_as_final_answer"],
                    "followup": {
                        "focus": "convergence",
                        "handoff": {"needs_convergence_tuning_first": True},
                        "convergence_summary": {
                            "max_iterations": 120,
                            "file_count": 1,
                            "residual_trend_counts": {"improving": 1},
                            "worst_final_residual": 0.02,
                        },
                        "tuning_hints": ["Keep the current setup mostly intact and tune tolerances or iteration limits gradually."],
                        "priority_issues": [{"category": "convergence"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_convergence_tuning_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    plan_id = next(
        item["plan_id"]
        for item in prompt_payload["data"]["edit_execution_plans"]
        if item["target_files"] == ["system/controlDict"]
        and any(
            artifact.get("parameter") == "deltaT"
            for artifact in item.get("artifacts", [])
            if isinstance(artifact, dict)
        )
    )

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=plan_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["action_kind"] == "execute_guarded_edit_plan"
    assert "execution_result" in data["output_contract"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    assert data["execution_result"]["changed_files"] == [str(control_dict)]
    assert control_dict.read_text(encoding="utf-8") == (
        "application icoFoam;\ndeltaT 0.005;\nmaxCo 0.5;\nendTime 100;\n"
    )
    backup_file = control_dict.with_name("controlDict.cae-cli.bak")
    assert backup_file.exists()
    assert "deltaT 0.01;" in backup_file.read_text(encoding="utf-8")


def test_tool_execute_guarded_edit_plan_keeps_structured_patch_plans_preview_only(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    boundary_dir = results_dir / "constant" / "polyMesh"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    boundary_file = boundary_dir / "boundary"
    boundary_file.write_text(
        "4\n(\ninlet\n{\n    type patch;\n}\n)\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL ERROR: cannot find patch field",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "patch field failed"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["constant/polyMesh/boundary"]
    )

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "unsupported_executor"
    assert data["execution_result"]["applied"] is False
    assert data["execution_result"]["executor_supported"] is False
    assert "type patch;" in boundary_file.read_text(encoding="utf-8")


def test_tool_execute_guarded_edit_plan_restores_openfoam_patch_name_entries(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    boundary_dir = results_dir / "constant" / "polyMesh"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    boundary_file = boundary_dir / "boundary"
    boundary_file.write_text(
        (
            "2\n(\ninlet_typo\n{\n    type patch;\n}\noutlet\n{\n    type patch;\n}\n)\n"
        ),
        encoding="utf-8",
    )
    zero_dir = results_dir / "0"
    zero_dir.mkdir(parents=True, exist_ok=True)
    velocity = zero_dir / "U"
    velocity.write_text(
        (
            "dimensions [0 1 -1 0 0 0 0];\n"
            "internalField uniform (0 0 0);\n"
            "boundaryField\n"
            "{\n"
            "    inlet\n"
            "    {\n"
            "        type fixedValue;\n"
            "        value uniform (1 0 0);\n"
            "    }\n"
            "    outlet\n"
            "    {\n"
            "        type zeroGradient;\n"
            "    }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL ERROR: cannot find patch inlet_typo in field U",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "boundary patch name mismatch"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["constant/polyMesh/boundary"]
        and any(
            operation.get("operation_kind") == "rename_declared_symbols"
            and operation.get("selector_mode") == "patch_name_entries"
            for operation in item.get("operations", [])
            if isinstance(operation, dict)
        )
    )

    preview_payload = tool_selected_edit_execution_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )
    assert preview_payload["ok"] is True
    preview_data = preview_payload["data"]
    assert preview_data["dry_run_validation"]["status"] == "ready_for_write_guard"
    assert preview_data["dry_run_validation"]["write_guard_passed"] is True
    assert preview_data["dry_run_validation"]["selector_checks"][0]["missing_tokens"] == [
        "inlet_typo"
    ]
    assert preview_data["dry_run_validation"]["selector_checks"][0]["field_only_tokens"] == [
        "inlet"
    ]

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    assert data["execution_result"]["executor_supported"] is True
    assert data["execution_result"]["changed_files"] == [str(boundary_file)]
    updated_text = boundary_file.read_text(encoding="utf-8")
    assert "inlet_typo" not in updated_text
    assert "\ninlet\n{\n" in updated_text
    backup_file = boundary_file.with_name("boundary.cae-cli.bak")
    assert backup_file.exists()
    assert "inlet_typo" in backup_file.read_text(encoding="utf-8")


def test_tool_execute_guarded_edit_plan_restores_multiple_openfoam_patch_name_entries(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    boundary_dir = results_dir / "constant" / "polyMesh"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    boundary_file = boundary_dir / "boundary"
    boundary_file.write_text(
        (
            "3\n(\ninlet_typo\n{\n    type patch;\n}\nwall_wrong\n{\n    type wall;\n}\noutlet\n{\n    type patch;\n}\n)\n"
        ),
        encoding="utf-8",
    )
    zero_dir = results_dir / "0"
    zero_dir.mkdir(parents=True, exist_ok=True)
    velocity = zero_dir / "U"
    velocity.write_text(
        (
            "dimensions [0 1 -1 0 0 0 0];\n"
            "internalField uniform (0 0 0);\n"
            "boundaryField\n"
            "{\n"
            "    inlet\n"
            "    {\n"
            "        type fixedValue;\n"
            "        value uniform (1 0 0);\n"
            "    }\n"
            "    wall\n"
            "    {\n"
            "        type fixedValue;\n"
            "        value uniform (0 0 0);\n"
            "    }\n"
            "    outlet\n"
            "    {\n"
            "        type zeroGradient;\n"
            "    }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL ERROR: cannot find patch names in field U",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "multiple boundary patch name mismatches"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["constant/polyMesh/boundary"]
        and any(
            operation.get("operation_kind") == "rename_declared_symbols"
            and operation.get("selector_mode") == "patch_name_entries"
            for operation in item.get("operations", [])
            if isinstance(operation, dict)
        )
    )

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    assert data["execution_result"]["executor_supported"] is True
    assert data["execution_result"]["changed_files"] == [str(boundary_file)]
    assert len(data["execution_result"]["structured_patch_changes"]) == 2
    updated_text = boundary_file.read_text(encoding="utf-8")
    assert "inlet_typo" not in updated_text
    assert "wall_wrong" not in updated_text
    assert "\ninlet\n{\n" in updated_text
    assert "\nwall\n{\n" in updated_text
    backup_file = boundary_file.with_name("boundary.cae-cli.bak")
    assert backup_file.exists()
    backup_text = backup_file.read_text(encoding="utf-8")
    assert "inlet_typo" in backup_text
    assert "wall_wrong" in backup_text


def test_tool_execute_guarded_edit_plan_rejects_ambiguous_openfoam_patch_name_entries(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    boundary_dir = results_dir / "constant" / "polyMesh"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    boundary_file = boundary_dir / "boundary"
    original_text = (
        "3\n(\ninlet_typo\n{\n    type patch;\n}\ninlet_wrong\n{\n    type patch;\n}\noutlet\n{\n    type patch;\n}\n)\n"
    )
    boundary_file.write_text(original_text, encoding="utf-8")
    zero_dir = results_dir / "0"
    zero_dir.mkdir(parents=True, exist_ok=True)
    velocity = zero_dir / "U"
    velocity.write_text(
        (
            "dimensions [0 1 -1 0 0 0 0];\n"
            "internalField uniform (0 0 0);\n"
            "boundaryField\n"
            "{\n"
            "    inlet\n"
            "    {\n"
            "        type fixedValue;\n"
            "        value uniform (1 0 0);\n"
            "    }\n"
            "    inlet2\n"
            "    {\n"
            "        type fixedValue;\n"
            "        value uniform (0 0 0);\n"
            "    }\n"
            "    outlet\n"
            "    {\n"
            "        type zeroGradient;\n"
            "    }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL ERROR: boundary patch names ambiguous",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "ambiguous boundary patch name mismatch"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["constant/polyMesh/boundary"]
        and any(
            operation.get("operation_kind") == "rename_declared_symbols"
            and operation.get("selector_mode") == "patch_name_entries"
            for operation in item.get("operations", [])
            if isinstance(operation, dict)
        )
    )

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "unsupported_executor"
    assert data["execution_result"]["applied"] is False
    assert data["execution_result"]["executor_supported"] is False
    assert "pairing_error=" in data["execution_result"]["message"]
    assert boundary_file.read_text(encoding="utf-8") == original_text
    assert not boundary_file.with_name("boundary.cae-cli.bak").exists()


def test_tool_execute_guarded_edit_plan_restores_required_openfoam_case_layout(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL ERROR: cannot find patch field",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "missing case layout"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["<case_dir>"]
        and any(
            operation.get("operation_kind") == "restore_required_layout"
            for operation in item.get("operations", [])
            if isinstance(operation, dict)
        )
    )

    preview_payload = tool_selected_edit_execution_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )
    assert preview_payload["ok"] is True
    preview_data = preview_payload["data"]
    assert preview_data["dry_run_validation"]["status"] == "ready_for_write_guard"
    assert preview_data["dry_run_validation"]["write_guard_passed"] is True
    assert preview_data["dry_run_validation"]["selector_checks"][0]["missing_tokens"] == [
        "0/",
        "constant/",
        "system/",
    ]

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    assert data["execution_result"]["executor_supported"] is True
    assert sorted(data["execution_result"]["created_paths"]) == sorted(
        [
            str(results_dir / "0"),
            str(results_dir / "constant"),
            str(results_dir / "system"),
        ]
    )
    assert (results_dir / "0").is_dir()
    assert (results_dir / "constant").is_dir()
    assert (results_dir / "system").is_dir()


def test_tool_execute_guarded_edit_plan_restores_openfoam_patch_field_entries(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    boundary_dir = results_dir / "constant" / "polyMesh"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    boundary_file = boundary_dir / "boundary"
    boundary_file.write_text(
        "2\n(\ninlet\n{\n    type patch;\n}\noutlet\n{\n    type patch;\n}\n)\n",
        encoding="utf-8",
    )
    zero_dir = results_dir / "0"
    zero_dir.mkdir(parents=True, exist_ok=True)
    velocity = zero_dir / "U"
    velocity.write_text(
        (
            "dimensions [0 1 -1 0 0 0 0];\n"
            "internalField uniform (0 0 0);\n"
            "boundaryField\n"
            "{\n"
            "    inlet\n"
            "    {\n"
            "        type fixedValue;\n"
            "        value uniform (1 0 0);\n"
            "    }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL ERROR: cannot find patchField entry for outlet",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "boundary field missing outlet patch entry"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["0/*"]
        and any(
            operation.get("operation_kind") == "repair_missing_entries"
            and operation.get("selector_mode") == "patch_field_entries"
            for operation in item.get("operations", [])
            if isinstance(operation, dict)
        )
    )

    preview_payload = tool_selected_edit_execution_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )
    assert preview_payload["ok"] is True
    preview_data = preview_payload["data"]
    assert preview_data["dry_run_validation"]["status"] == "ready_for_write_guard"
    assert preview_data["dry_run_validation"]["write_guard_passed"] is True
    assert preview_data["dry_run_validation"]["selector_checks"][0]["missing_tokens"] == [
        "outlet"
    ]

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    assert data["execution_result"]["executor_supported"] is True
    assert data["execution_result"]["changed_files"] == [str(velocity)]
    updated_text = velocity.read_text(encoding="utf-8")
    assert "outlet" in updated_text
    assert "type zeroGradient;" in updated_text
    backup_file = velocity.with_name("U.cae-cli.bak")
    assert backup_file.exists()
    assert "outlet" not in backup_file.read_text(encoding="utf-8")


def test_tool_execute_guarded_edit_plan_restores_openfoam_patch_field_entries_with_wall_noslip(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    boundary_dir = results_dir / "constant" / "polyMesh"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    boundary_file = boundary_dir / "boundary"
    boundary_file.write_text(
        "2\n(\nwall\n{\n    type wall;\n}\noutlet\n{\n    type patch;\n}\n)\n",
        encoding="utf-8",
    )
    zero_dir = results_dir / "0"
    zero_dir.mkdir(parents=True, exist_ok=True)
    velocity = zero_dir / "U"
    velocity.write_text(
        (
            "FoamFile\n"
            "{\n"
            "    class volVectorField;\n"
            "}\n"
            "dimensions [0 1 -1 0 0 0 0];\n"
            "internalField uniform (0 0 0);\n"
            "boundaryField\n"
            "{\n"
            "    outlet\n"
            "    {\n"
            "        type zeroGradient;\n"
            "    }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL ERROR: cannot find patchField entry for wall",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "boundary field missing wall patch entry"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["0/*"]
        and any(
            operation.get("operation_kind") == "repair_missing_entries"
            and operation.get("selector_mode") == "patch_field_entries"
            for operation in item.get("operations", [])
            if isinstance(operation, dict)
        )
    )

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    updated_text = velocity.read_text(encoding="utf-8")
    assert "wall" in updated_text
    assert "type noSlip;" in updated_text


def test_tool_execute_guarded_edit_plan_restores_openfoam_patch_field_entries_with_inlet_fixed_value(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    boundary_dir = results_dir / "constant" / "polyMesh"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    boundary_file = boundary_dir / "boundary"
    boundary_file.write_text(
        "1\n(\ninlet\n{\n    type patch;\n}\n)\n",
        encoding="utf-8",
    )
    zero_dir = results_dir / "0"
    zero_dir.mkdir(parents=True, exist_ok=True)
    pressure = zero_dir / "p"
    pressure.write_text(
        (
            "FoamFile\n"
            "{\n"
            "    class volScalarField;\n"
            "}\n"
            "dimensions [0 2 -2 0 0 0 0];\n"
            "internalField uniform 0;\n"
            "boundaryField\n"
            "{\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL ERROR: cannot find patchField entry for inlet",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "boundary field missing inlet patch entry"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["0/*"]
        and any(
            operation.get("operation_kind") == "repair_missing_entries"
            and operation.get("selector_mode") == "patch_field_entries"
            for operation in item.get("operations", [])
            if isinstance(operation, dict)
        )
    )

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    updated_text = pressure.read_text(encoding="utf-8")
    assert "inlet" in updated_text
    assert "type fixedValue;" in updated_text
    assert "value uniform 0;" in updated_text


def test_tool_execute_guarded_edit_plan_restores_control_dict_write_interval(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    system_dir = results_dir / "system"
    system_dir.mkdir(parents=True, exist_ok=True)
    control_dict = system_dir / "controlDict"
    control_dict.write_text(
        "application icoFoam;\nstartFrom startTime;\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL IO ERROR: keyword writeInterval is undefined",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "controlDict missing writeInterval"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["system/controlDict"]
    )

    preview_payload = tool_selected_edit_execution_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )
    assert preview_payload["ok"] is True
    preview_data = preview_payload["data"]
    assert preview_data["dry_run_validation"]["status"] == "ready_for_write_guard"
    assert preview_data["dry_run_validation"]["write_guard_passed"] is True
    assert preview_data["dry_run_validation"]["selector_checks"][0]["matched_tokens"] == [
        "application",
        "startFrom",
    ]
    assert preview_data["dry_run_validation"]["selector_checks"][0]["missing_tokens"] == [
        "writeInterval"
    ]

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    assert data["execution_result"]["executor_supported"] is True
    assert data["execution_result"]["changed_files"] == [str(control_dict)]
    assert control_dict.read_text(encoding="utf-8") == (
        "application icoFoam;\nstartFrom startTime;\nwriteInterval 1;\n"
    )
    backup_file = control_dict.with_name("controlDict.cae-cli.bak")
    assert backup_file.exists()
    assert backup_file.read_text(encoding="utf-8") == (
        "application icoFoam;\nstartFrom startTime;\n"
    )


def test_tool_execute_guarded_edit_plan_restores_fvsolution_relaxation_factors(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    system_dir = results_dir / "system"
    system_dir.mkdir(parents=True, exist_ok=True)
    fvsolution = system_dir / "fvSolution"
    fvsolution.write_text(
        "solvers\n{\n    p\n    {\n        tolerance 1e-06;\n    }\n}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "openfoam",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-openfoam.log",
                            "status_reason": "FOAM FATAL IO ERROR: relaxationFactors not found",
                            "log_files": ["docker-openfoam.log"],
                            "input_files": ["case.foam"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "fvSolution missing relaxationFactors"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["system/fvSolution"]
    )

    preview_payload = tool_selected_edit_execution_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )
    assert preview_payload["ok"] is True
    preview_data = preview_payload["data"]
    assert preview_data["dry_run_validation"]["status"] == "ready_for_write_guard"
    assert preview_data["dry_run_validation"]["write_guard_passed"] is True
    assert preview_data["dry_run_validation"]["selector_checks"][0]["matched_tokens"] == [
        "solvers"
    ]
    assert preview_data["dry_run_validation"]["selector_checks"][0]["missing_tokens"] == [
        "relaxationFactors"
    ]

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    assert data["execution_result"]["executor_supported"] is True
    assert data["execution_result"]["changed_files"] == [str(fvsolution)]
    updated_text = fvsolution.read_text(encoding="utf-8")
    assert "relaxationFactors" in updated_text
    assert "p 0.3;" in updated_text
    assert "U 0.7;" in updated_text
    backup_file = fvsolution.with_name("fvSolution.cae-cli.bak")
    assert backup_file.exists()
    assert "relaxationFactors" not in backup_file.read_text(encoding="utf-8")


def test_tool_execute_guarded_edit_plan_applies_export_reference_patch(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    export_file = results_dir / "case.export"
    export_file.write_text(
        "F comm wrong.comm D 1\nF mmed mesh.med D 2\nP working_dir ./\n",
        encoding="utf-8",
    )
    (results_dir / "case.comm").write_text(
        "mesh/material include references\ncommand pairing\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cae.mcp_server._build_diagnosis_payload",
        lambda **kwargs: (
            {
                "issue_count": 1,
                "summary": {"risk_level": "high"},
                "meta": {
                    "results_dir": str(results_dir),
                    "detected_solver": "code_aster",
                    "solver_status": "failed",
                },
                "routing": {
                    "route": "runtime_remediation",
                    "decision_source": "solver_status_gate",
                    "recommended_next_action": "Inspect the solver runtime failure before attempting physics diagnosis.",
                    "blocked_actions": ["physics_diagnosis"],
                    "followup": {
                        "focus": "runtime",
                        "handoff": {"needs_runtime_fix_first": True},
                        "checklist": [{"check": "command", "instruction": "Check the entry command and solver executable invocation before retrying the run."}],
                        "artifact_snapshot": {
                            "primary_log": "docker-code_aster.log",
                            "status_reason": "No such file or directory: case.comm",
                            "log_files": ["docker-code_aster.log"],
                            "input_files": ["case.export", "case.comm"],
                        },
                        "priority_issues": [{"category": "solver_runtime", "message": "command file failed"}],
                    },
                },
            },
            None,
        ),
    )

    prompt_payload = tool_runtime_remediation_prompt(results_dir=str(results_dir))
    assert prompt_payload["ok"] is True
    payload_id = next(
        item["payload_id"]
        for item in prompt_payload["data"]["edit_payload_templates"]
        if item["target_files"] == ["<case>.export"]
    )

    payload = tool_execute_guarded_edit_plan(
        results_dir=str(results_dir),
        selection_id=payload_id,
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["execution_result"]["status"] == "applied"
    assert data["execution_result"]["applied"] is True
    assert data["execution_result"]["executor_supported"] is True
    assert data["execution_result"]["changed_files"] == [str(export_file)]
    assert export_file.read_text(encoding="utf-8").startswith("F comm case.comm D 1")
    backup_file = export_file.with_name("case.export.cae-cli.bak")
    assert backup_file.exists()
    assert backup_file.read_text(encoding="utf-8").startswith("F comm wrong.comm D 1")


def test_tool_physics_interpretation_prompt_builds_grounded_prompt(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_physics_diagnosis",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "physics_diagnosis",
                "actual_route": "physics_diagnosis",
                "decision_source": "diagnosis_plan",
                "solver": "calculix",
                "solver_status": "success",
                "recommended_next_action": "Inspect boundary constraints",
                "summary": {"risk_level": "medium"},
                "followup": {
                    "artifact_snapshot": {
                        "primary_log": "case.sta",
                        "result_files": ["model.frd"],
                    },
                    "top_issue": {"message": "Boundary condition needs review"},
                    "first_action": "Inspect boundary constraints",
                    "similar_cases": [{"name": "beam_case"}],
                    "result_readiness": {"ready_for_interpretation": True},
                },
            },
        },
    )

    payload = tool_physics_interpretation_prompt(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["action_kind"] == "physics_interpretation_prompt"
    assert data["result_readiness"]["ready_for_interpretation"] is True
    assert "Interpret the current solver results" in data["prompt"]
    assert "Solver-run evidence preview:" in data["prompt"]
    assert "Solver-run branch:" in data["prompt"]
    assert data["solver_run"]["primary_log"] == "case.sta"
    assert data["solver_run"]["result_files"] == ["model.frd"]
    assert data["solver_run_branch"]["branch"] == "result_interpretation"
    assert data["similar_cases"][0]["name"] == "beam_case"


def test_tool_evidence_collection_plan_builds_ordered_steps(monkeypatch, workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_evidence_expansion",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "evidence_expansion",
                "actual_route": "evidence_expansion",
                "decision_source": "solver_status_gate",
                "solver": "unknown",
                "solver_status": "unknown",
                "recommended_next_action": "Inspect logs and artifacts to classify solver status before auto-fix or physics diagnosis.",
                "solver_run": {
                    "primary_log": "logs/unknown.log",
                    "has_primary_log": True,
                    "text_source_count": 2,
                    "log_file_count": 1,
                    "result_file_count": 0,
                    "log_files": ["logs/unknown.log"],
                    "text_sources": [
                        {"path": "logs/unknown.log", "kind": "runtime_log"},
                        {"path": "case.stderr", "kind": "stderr"},
                    ],
                    "result_files": [],
                },
                "summary": {"risk_level": "low"},
                "followup": {
                    "classification_gaps": ["primary_log", "text_sources"],
                    "next_collection_targets": ["primary_log", "text_sources"],
                    "evidence_status": {"has_primary_log": False},
                },
            },
        },
    )

    payload = tool_evidence_collection_plan(results_dir=str(results_dir))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["action_kind"] == "evidence_collection_plan"
    assert data["collection_steps"][0]["target"] == "primary_log"
    assert data["collection_steps"][0]["done_when"]
    assert data["solver_run"]["primary_log"] == "logs/unknown.log"
    assert data["solver_run_branch"]["branch"] == "collect_result_artifacts"
    assert data["available_evidence"]["has_primary_log"] is True
    assert data["available_evidence"]["text_source_count"] == 2
    assert data["evidence_status"]["has_primary_log"] is False


def test_tool_evidence_collection_plan_normalizes_mixed_solver_run_snapshot(
    monkeypatch, workspace: Path
) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "cae.mcp_server.tool_evidence_expansion",
        lambda **kwargs: {
            "ok": True,
            "data": {
                "applicable": True,
                "expected_route": "evidence_expansion",
                "actual_route": "evidence_expansion",
                "decision_source": "solver_status_gate",
                "solver": "unknown",
                "solver_status": "unknown",
                "recommended_next_action": "Inspect mixed solver artifacts before routing.",
                "solver_run": {
                    "primary_log": "logs\\log.icoFoam",
                    "has_primary_log": True,
                    "text_source_count": "not-a-number",
                    "log_file_count": "not-a-number",
                    "result_file_count": "not-a-number",
                    "input_files": [
                        "system\\controlDict",
                        "case\\inv_channel_smoke.cfg",
                        "system\\controlDict",
                    ],
                    "log_files": [
                        "logs\\log.icoFoam",
                        "logs/docker-su2.log",
                        "logs/docker-su2.log",
                    ],
                    "result_files": [
                        "post\\U.vtk",
                        "history.csv",
                        "post\\U.vtk",
                    ],
                    "text_sources": [
                        "logs\\log.icoFoam",
                        {"path": "logs/log.icoFoam", "kind": "runtime_log"},
                        {"path": "history.csv", "kind": "solver_history"},
                        "logs\\docker-su2.log",
                        {"path": "logs/docker-su2.log", "kind": "runtime_log"},
                    ],
                },
                "summary": {"risk_level": "low"},
                "followup": {
                    "classification_gaps": ["runtime_metadata"],
                    "next_collection_targets": ["runtime_metadata"],
                    "evidence_status": {"has_primary_log": True},
                },
            },
        },
    )

    payload = tool_evidence_collection_plan(results_dir=str(results_dir))

    assert payload["ok"] is True
    solver_run = payload["data"]["solver_run"]
    assert solver_run["primary_log"] == "logs/log.icoFoam"
    assert solver_run["input_files"] == ["system/controlDict", "case/inv_channel_smoke.cfg"]
    assert solver_run["log_files"] == ["logs/log.icoFoam", "logs/docker-su2.log"]
    assert solver_run["result_files"] == ["post/U.vtk", "history.csv"]
    assert solver_run["text_sources"] == [
        {"path": "logs/log.icoFoam", "kind": "runtime_log"},
        {"path": "history.csv", "kind": "solver_history"},
        {"path": "logs/docker-su2.log", "kind": "runtime_log"},
    ]
    assert payload["data"]["solver_run_branch"]["branch"] == "classify_mixed_evidence"
    assert payload["data"]["available_evidence"]["text_source_count"] == 3
    assert payload["data"]["available_evidence"]["log_file_count"] == 2
    assert payload["data"]["available_evidence"]["result_file_count"] == 2


def test_tool_inp_check_reports_unknown_keyword(workspace: Path) -> None:
    inp = workspace / "x.inp"
    inp.write_text("*FOO\n1,2,3\n", encoding="utf-8")

    payload = tool_inp_check(inp_file=str(inp))

    assert payload["ok"] is True
    assert payload["data"]["valid"] is False
    assert "*FOO" in payload["data"]["unknown_keywords"]
