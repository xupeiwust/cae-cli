from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from cae.ai.diagnose import DiagnosticIssue, _apply_history_consistency_guardrails


def _make_workspace() -> Path:
    root = Path(__file__).parent / ".tmp_diagnosis_history"
    root.mkdir(exist_ok=True)
    workspace = root / uuid4().hex
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def test_history_guardrail_boosts_consistent_issue_score() -> None:
    workspace = _make_workspace()
    try:
        db_path = workspace / "diagnosis_history.db"
        seed_issue = DiagnosticIssue(
            severity="warning",
            category="convergence",
            message="increment did not converge",
            evidence_line="case.stderr:4: increment did not converge",
            evidence_score=0.80,
            evidence_support_count=2,
        )

        _apply_history_consistency_guardrails([seed_issue], history_db_path=db_path)
        _apply_history_consistency_guardrails([seed_issue], history_db_path=db_path)
        boosted = _apply_history_consistency_guardrails([seed_issue], history_db_path=db_path)

        assert len(boosted) == 1
        issue = boosted[0]
        assert (issue.history_hits or 0) >= 2
        assert issue.evidence_score is not None
        assert issue.evidence_score >= 0.85
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_history_guardrail_downgrades_high_conflict_error() -> None:
    workspace = _make_workspace()
    try:
        db_path = workspace / "diagnosis_history.db"
        conflict_issue = DiagnosticIssue(
            severity="warning",
            category="convergence",
            message="increment did not converge",
            evidence_line="case.stderr:6: increment did not converge",
            evidence_score=0.65,
            evidence_support_count=1,
            evidence_conflict="STA trend indicates healthy convergence.",
        )
        _apply_history_consistency_guardrails([conflict_issue], history_db_path=db_path)
        _apply_history_consistency_guardrails([conflict_issue], history_db_path=db_path)
        _apply_history_consistency_guardrails([conflict_issue], history_db_path=db_path)

        strong_error = DiagnosticIssue(
            severity="error",
            category="convergence",
            message="increment did not converge",
            evidence_line="case.stderr:6: increment did not converge",
            evidence_score=0.92,
            evidence_support_count=2,
        )

        adjusted = _apply_history_consistency_guardrails([strong_error], history_db_path=db_path)

        assert len(adjusted) == 1
        issue = adjusted[0]
        assert issue.severity == "warning"
        assert issue.evidence_score is not None
        assert issue.evidence_score <= 0.84
        assert "Historical consistency low" in (issue.evidence_conflict or "")
        assert (issue.history_conflict_rate or 0.0) >= 0.5
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_history_guardrail_uses_similar_issue_when_exact_key_missing() -> None:
    workspace = _make_workspace()
    try:
        db_path = workspace / "diagnosis_history.db"
        seed_issue = DiagnosticIssue(
            severity="warning",
            category="convergence",
            message="increment did not converge at step one",
            evidence_line="case.stderr:10: increment did not converge at step one",
            evidence_score=0.68,
            evidence_support_count=1,
            evidence_conflict="STA trend indicates healthy convergence.",
        )
        _apply_history_consistency_guardrails([seed_issue], history_db_path=db_path)
        _apply_history_consistency_guardrails([seed_issue], history_db_path=db_path)
        _apply_history_consistency_guardrails([seed_issue], history_db_path=db_path)

        exact_missing = DiagnosticIssue(
            severity="error",
            category="convergence",
            message="increment did not converge at step two",
            evidence_line="case.stderr:18: increment did not converge at step two",
            evidence_score=0.90,
            evidence_support_count=2,
        )

        adjusted = _apply_history_consistency_guardrails([exact_missing], history_db_path=db_path)

        assert len(adjusted) == 1
        issue = adjusted[0]
        assert issue.history_hits in (0, None)
        assert issue.history_similarity is not None
        assert issue.history_similarity >= 0.55
        assert issue.history_similar_hits is not None
        assert issue.history_similar_hits >= 3
        assert issue.severity == "warning"
        assert "Historical similar issues unstable" in (issue.evidence_conflict or "")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
