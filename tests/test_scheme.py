from pathlib import Path

from pydantic import ValidationError
import pytest

from app.scheme import (
    FailureWhy,
    OutputRubric,
    ProveReport,
    RubricCheck,
    VerticalScore,
    RUBRIC_KEYS,
)


def test_rubric_why_required_on_fail() -> None:
    with pytest.raises(ValidationError):
        RubricCheck(passed=False, why="")
    ok = RubricCheck(passed=False, why="WHY: off-job.")
    assert ok.why.startswith("WHY:")


def test_output_rubric_keys() -> None:
    rubric = OutputRubric(
        on_job=RubricCheck(passed=True),
        complete=RubricCheck(passed=True),
        safe=RubricCheck(passed=True),
        cites_skill_steps=RubricCheck(passed=True),
    )
    assert [key for key, _item in rubric.as_items()] == list(RUBRIC_KEYS)
    assert rubric.all_passed() is True


def test_models_are_pydantic() -> None:
    assert FailureWhy.model_fields["why"].is_required()
    assert "weight" in VerticalScore.model_fields
    assert VerticalScore.model_fields["weight"].is_required() is False
    assert "composite_0_100" in ProveReport.model_fields


def test_no_hardcoded_403030_acceptance() -> None:
    roots = [Path("app"), Path("README.md"), Path("tests")]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        else:
            files.extend(p for p in root.rglob("*") if p.suffix in {".py", ".html", ".js", ".css", ".md"})
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "WEIGHTS" not in text or "provisional" in text.lower() or path.name == "test_scheme.py"
        if path.suffix == ".py" and path.name != "test_scheme.py":
            assert '"wake_recall": 40' not in text
            assert "wake_recall: 40" not in text
