from app.gate import Store
from app.prove import run_prove
from app.scheme import ProveRequest
from app.cli import run_prove as cli_prove


def test_teachable_why_and_evidence_surfaced(store: Store) -> None:
    session = store.create("Draft release notes from PR diffs for the changelog.")
    store.build(
        session,
        when="Release notes from a PR or changelog.",
        not_when="Marketing, blog posts, or product launch prose.",
        body="Draft the notes from the PR diff.",
        should=["Draft release notes from this PR diff for the changelog."],
        should_not=["Write a blog post about our product launch."],
        near_miss=["Summarize this meeting for the team."],
        with_skill=["Changelog notes drafted from the PR diff."],
        without_skill=["A 1200-word blog post about our product launch."],
        continue_to_prove=True,
    )
    store.prove(session)
    assert session.proved is True
    assert session.prove_report
    assert "wake" in session.prove_report
    assert "output" in session.prove_report
    assert "composite_0_100" not in session.prove_report
    families = {row["family"] for row in session.benchmarks}
    assert families == {"wake", "output"}
    assert all(row["evidence"]["fixture"] for row in session.benchmarks)
    wake = session.prove_report["wake"]
    assert wake["harness_honesty"] is True
    assert "should" in wake["trigger_rates"]
    output = session.prove_report["output"]["cases"]
    assert {row["kind"] for row in output} == {"with", "without"}
    assert all(row["assertions"] for row in output)


def test_vague_wake_mismatch_has_why_and_evidence(store: Store) -> None:
    session = store.create("Summarize things for people.")
    store.build(
        session,
        when="When someone asks you to summarize.",
        not_when="Nothing in particular.",
        should=["Summarize the weekly notes."],
        should_not=["Summarize this meeting for the team."],
        continue_to_prove=True,
    )
    store.prove(session)
    failed = [row for row in session.benchmarks if row.get("badge") == "MISMATCH"]
    assert failed
    assert any(row["family"] == "wake" for row in failed)
    assert all(row["why"] and row["evidence"]["fixture"] for row in failed)


def test_run_prove_shells_out_to_cli() -> None:
    report = run_prove(
        job="Draft release notes from PR diffs for the changelog.",
        when="Release notes from a PR or changelog.",
        not_when="Marketing or blog posts.",
        body="Draft the notes from the PR diff.",
        should=["Draft release notes from this PR diff for the changelog."],
        should_not=["Write a blog post about our product launch."],
        near_miss=["Summarize this meeting for the team."],
        with_skill=["Changelog notes from the PR diff."],
        without_skill=["A 1200-word blog post about our product launch."],
    )
    assert report.via == "cli"
    assert report.wake.cases
    assert report.output.cases
    kinds = {c.kind for c in report.wake.cases}
    assert "should" in kinds
    assert "should_not" in kinds
    assert "near_miss" in kinds
    assert {c.kind for c in report.output.cases} == {"with", "without"}
    assert all(c.evidence.fixture for c in report.wake.cases)
    assert all(c.evidence.fixture for c in report.output.cases)


def test_cli_prove_scheme_direct() -> None:
    resp = cli_prove(
        ProveRequest(
            job="Draft release notes from PR diffs for the changelog.",
            when="Release notes from a PR or changelog.",
            not_when="Marketing or blog posts.",
            body="Draft the notes from the PR diff.",
            should=["Draft release notes from this PR diff for the changelog."],
            should_not=["Write a blog post about our product launch."],
            with_skill=["Changelog notes from the PR diff."],
            without_skill=["A 1200-word blog post about our product launch."],
        )
    )
    assert resp.via == "cli"
    assert resp.wake.recall is not None
    assert resp.wake.precision is not None


def test_keep_ignores_mismatches_no_numeric_floor(store: Store, skills_dir) -> None:
    session = store.create("Summarize things for people.")
    store.build(
        session,
        when="When someone asks you to summarize.",
        not_when="Nothing in particular.",
        should=["Summarize the weekly notes."],
        should_not=["Summarize this meeting for the team."],
        continue_to_prove=True,
    )
    store.prove(session)
    assert any(not row.get("matched", row.get("passed")) for row in session.benchmarks)
    path = store.keep(session, skills_dir)
    assert path.exists()
    assert session.disposed == "keep"
