from pathlib import Path

from pydantic import ValidationError
import pytest

from app.scheme import Evidence, OutputCase, ProveReport, WakeCase, WakeReport, OutputReport


def test_evidence_required_on_wake_case() -> None:
    with pytest.raises(ValidationError):
        WakeCase(
            kind="should",
            prompt="x",
            woke=False,
            expected_wake=True,
            matched=False,
            trigger_rate=0,
            harness_honest=True,
            evidence=Evidence(fixture=""),
            why="WHY: missed.",
        )


def test_why_required_on_wake_mismatch() -> None:
    with pytest.raises(ValidationError):
        WakeCase(
            kind="should",
            prompt="x",
            woke=False,
            expected_wake=True,
            matched=False,
            trigger_rate=0,
            harness_honest=True,
            evidence=Evidence(fixture="x"),
            why="",
        )


def test_prove_report_is_wake_and_output_only() -> None:
    report = ProveReport(wake=WakeReport(cases=[]), output=OutputReport(cases=[]))
    data = report.model_dump()
    assert set(data) >= {"wake", "output", "via"}
    assert "composite_0_100" not in ProveReport.model_fields
    assert report.via == "cli"


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
        if path.suffix == ".py" and path.name != "test_scheme.py":
            assert '"wake_recall": 40' not in text
            assert "wake_recall: 40" not in text
        assert "keep floor" not in text.lower() or "no numeric" in text.lower() or "not a keep" in text.lower()


def test_output_case_needs_evidence() -> None:
    with pytest.raises(ValidationError):
        OutputCase(
            kind="with",
            sample="x",
            judge="deterministic",
            passed=True,
            evidence=Evidence(fixture=""),
            why="ok",
        )
