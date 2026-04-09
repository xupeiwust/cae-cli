from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from cae.ai.diagnose import _check_inp_file_quality


def _make_workspace() -> Path:
    root = Path(__file__).parent / ".tmp_step_balance"
    root.mkdir(exist_ok=True)
    workspace = root / uuid4().hex
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def test_check_inp_file_quality_detects_unclosed_step_block() -> None:
    workspace = _make_workspace()
    try:
        inp_file = workspace / "model.inp"
        inp_file.write_text(
            "*HEADING\n"
            "*NODE\n"
            "1, 0, 0, 0\n"
            "*STEP\n"
            "*STATIC\n"
            "0.1, 1.0\n",
            encoding="utf-8",
        )

        issues = _check_inp_file_quality(inp_file)

        assert any(
            issue.category == "input_syntax" and "*END STEP" in issue.message
            for issue in issues
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
