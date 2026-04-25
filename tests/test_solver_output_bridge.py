from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from cae.ai.diagnose import DiagnoseResult, diagnosis_result_to_dict, diagnose_results
from cae.ai.solver_output import (
    collect_solver_text_sources,
    extract_solver_convergence_metrics,
    summarize_solver_run,
)


def _make_workspace() -> Path:
    root = Path(__file__).parent / ".tmp_solver_output_bridge"
    root.mkdir(exist_ok=True)
    workspace = root / uuid4().hex
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def test_collect_solver_text_sources_includes_docker_logs_and_history() -> None:
    workspace = _make_workspace()
    try:
        (workspace / "docker-su2.log").write_text("Exit Success (SU2_CFD)\n", encoding="utf-8")
        (workspace / "history.csv").write_text(
            '"Time_Iter","Inner_Iter","rms[Rho]"\n0,0,-1.0\n',
            encoding="utf-8",
        )

        sources = collect_solver_text_sources(workspace)

        assert [path.name for path in sources] == ["docker-su2.log", "history.csv"]
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_collect_solver_text_sources_discovers_nested_openfoam_log() -> None:
    workspace = _make_workspace()
    try:
        logs_dir = workspace / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "log.icoFoam").write_text(
            "Courant Number mean: 0.10 max: 0.80\nEnd\n",
            encoding="utf-8",
        )

        sources = collect_solver_text_sources(workspace)
        relpaths = {str(path.relative_to(workspace)).replace("\\", "/") for path in sources}

        assert "logs/log.icoFoam" in relpaths
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_extract_solver_convergence_metrics_reads_su2_history() -> None:
    workspace = _make_workspace()
    try:
        (workspace / "docker-su2.log").write_text(
            "Maximum number of iterations reached (ITER = 50) before convergence.\n"
            "Exit Success (SU2_CFD)\n",
            encoding="utf-8",
        )
        (workspace / "history.csv").write_text(
            (
                '"Time_Iter","Outer_Iter","Inner_Iter","rms[Rho]","rms[RhoU]"\n'
                "0,0,0,-1.0,-0.5\n"
                "0,0,1,-2.0,-1.5\n"
                "0,0,2,-4.0,-3.0\n"
            ),
            encoding="utf-8",
        )

        metrics = extract_solver_convergence_metrics(workspace)

        assert len(metrics) == 1
        metric = metrics[0]
        assert metric["solver"] == "su2"
        assert metric["status"] == "NOT CONVERGED"
        assert metric["max_iter"] == 2
        assert metric["residual_trend"] == "decreasing"
        assert abs(float(metric["final_residual"]) - 1.0e-3) < 1e-12
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_extract_solver_convergence_metrics_reads_openfoam_log() -> None:
    workspace = _make_workspace()
    try:
        (workspace / "docker-openfoam.log").write_text(
            (
                "Time = 0.05s\n"
                "Courant Number mean: 0.10 max: 0.80\n"
                "smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 1.0e-03, No Iterations 5\n"
                "Time = 0.10s\n"
                "Courant Number mean: 0.12 max: 0.85\n"
                "DICPCG:  Solving for p, Initial residual = 0.1, Final residual = 2.0e-05, No Iterations 8\n"
                "End\n"
            ),
            encoding="utf-8",
        )

        metrics = extract_solver_convergence_metrics(workspace)

        assert len(metrics) == 1
        metric = metrics[0]
        assert metric["solver"] == "openfoam"
        assert metric["status"] == "COMPLETED"
        assert metric["max_iter"] == 2
        assert metric["residual_trend"] == "decreasing"
        assert metric["final_time"] == 0.1
        assert metric["max_courant"] == 0.85
        assert metric["final_increment"] == 0.05
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_summarize_solver_run_detects_code_aster_success() -> None:
    workspace = _make_workspace()
    try:
        (workspace / "case.comm").write_text("DEBUT();\nFIN();\n", encoding="utf-8")
        (workspace / "docker-code_aster.log").write_text(
            (
                '<I> <FIN> ARRET NORMAL DANS "FIN" PAR APPEL A "JEFINI".\n'
                "--- DIAGNOSTIC JOB : OK\n"
            ),
            encoding="utf-8",
        )

        summary = summarize_solver_run(workspace)

        assert summary["solver"] == "code_aster"
        assert summary["status"] == "success"
        assert summary["primary_log"] == "docker-code_aster.log"
        assert summary["artifacts"]["input_files"] == ["case.comm"]
        assert any(item["kind"] == "runtime_log" for item in summary["text_sources"])
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_summarize_solver_run_uses_nested_openfoam_runtime_log() -> None:
    workspace = _make_workspace()
    try:
        (workspace / "system").mkdir(parents=True, exist_ok=True)
        (workspace / "constant").mkdir(parents=True, exist_ok=True)
        (workspace / "system" / "controlDict").write_text(
            "application icoFoam;\n",
            encoding="utf-8",
        )
        logs_dir = workspace / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "log.icoFoam").write_text(
            (
                "Time = 0.05\n"
                "Courant Number mean: 0.10 max: 0.80\n"
                "End\n"
            ),
            encoding="utf-8",
        )

        summary = summarize_solver_run(workspace)

        assert summary["solver"] == "openfoam"
        assert summary["status"] == "success"
        assert summary["primary_log"] == "log.icoFoam"
        assert "logs/log.icoFoam" in summary["artifacts"]["log_files"]
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_diagnosis_result_to_dict_includes_solver_summary_and_cross_solver_convergence() -> None:
    workspace = _make_workspace()
    try:
        (workspace / "docker-su2.log").write_text(
            "Maximum number of iterations reached (ITER = 50) before convergence.\n",
            encoding="utf-8",
        )
        (workspace / "history.csv").write_text(
            (
                '"Time_Iter","Outer_Iter","Inner_Iter","rms[Rho]"\n'
                "0,0,0,-1.0\n"
                "0,0,1,-3.0\n"
            ),
            encoding="utf-8",
        )

        payload = diagnosis_result_to_dict(
            DiagnoseResult(success=True),
            results_dir=workspace,
            inp_file=None,
            ai_enabled=False,
        )

        assert payload["solver_run"]["solver"] == "su2"
        assert payload["solver_run"]["status"] == "not_converged"
        assert payload["meta"]["detected_solver"] == "su2"
        assert payload["meta"]["solver_status"] == "not_converged"
        assert payload["convergence"]["files"][0]["solver"] == "su2"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_diagnose_results_adds_su2_not_converged_issue() -> None:
    workspace = _make_workspace()
    try:
        (workspace / "docker-su2.log").write_text(
            "Maximum number of iterations reached (ITER = 50) before convergence.\n",
            encoding="utf-8",
        )
        (workspace / "history.csv").write_text(
            (
                '"Time_Iter","Outer_Iter","Inner_Iter","rms[Rho]"\n'
                "0,0,0,-1.0\n"
                "0,0,1,-2.0\n"
            ),
            encoding="utf-8",
        )

        result = diagnose_results(workspace, client=None)

        convergence_issues = [issue for issue in result.issues if issue.category == "convergence"]
        assert convergence_issues
        assert any("before convergence" in issue.message.lower() for issue in convergence_issues)
        assert any(issue.location == "docker-su2.log" for issue in convergence_issues)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
