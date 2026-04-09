from __future__ import annotations

from io import StringIO
from pathlib import Path
import shutil
import uuid

from rich.console import Console

from cae.main import _print_solve_result
from cae.solvers.base import SolveResult


def _make_workspace_tmp() -> Path:
    root = Path(__file__).resolve().parent / ".tmp_solve_result_output"
    case_dir = root / uuid.uuid4().hex
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def _make_result(base_dir: Path, warnings: list[str]) -> SolveResult:
    output_dir = base_dir / "results"
    output_dir.mkdir()

    output_files = []
    for name, content in {
        "test.frd": "** fake frd",
        "test.dat": "** fake dat",
        "test.stderr": "\n".join(warnings),
    }.items():
        path = output_dir / name
        path.write_text(content, encoding="utf-8")
        output_files.append(path)

    return SolveResult(
        success=True,
        output_dir=output_dir,
        output_files=output_files,
        stdout="",
        stderr="\n".join(warnings),
        returncode=0,
        duration_seconds=0.2,
        warnings=warnings,
    )


def test_print_solve_result_marks_success_with_warnings(monkeypatch) -> None:
    from cae import main

    base_dir = _make_workspace_tmp()
    capture = StringIO()
    test_console = Console(file=capture, force_terminal=False, color_system=None, width=120)
    monkeypatch.setattr(main, "console", test_console)

    try:
        result = _make_result(base_dir, ["warning 1", "warning 2"])
        _print_solve_result(result, base_dir / "test.inp")
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    output = capture.getvalue()
    assert "求解完成（含警告）" in output
    assert "结果已生成，但检测到 2 条警告" in output
    assert "cae diagnose" in output


def test_print_solve_result_keeps_clean_success_message(monkeypatch) -> None:
    from cae import main

    base_dir = _make_workspace_tmp()
    capture = StringIO()
    test_console = Console(file=capture, force_terminal=False, color_system=None, width=120)
    monkeypatch.setattr(main, "console", test_console)

    try:
        result = _make_result(base_dir, [])
        _print_solve_result(result, base_dir / "test.inp")
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    output = capture.getvalue()
    assert "求解完成！" in output
    assert "求解完成（含警告）" not in output
    assert "结果已生成，但检测到" not in output
