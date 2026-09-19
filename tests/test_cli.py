import json
import subprocess
import sys
from pathlib import Path

from app.prove import run_rank
from app.scheme import RUBRIC_KEYS

ROOT = Path(__file__).resolve().parents[1]


def test_cli_prove_subprocess() -> None:
    payload = {
        "job": "Draft release notes from PR diffs for the changelog.",
        "when": "Release notes from a PR or changelog.",
        "not_when": "Marketing or blog posts.",
        "body": "Draft the notes from the PR diff.",
        "should": ["Draft release notes from this PR diff for the changelog."],
        "should_not": ["Write a blog post about our product launch."],
        "relevant": ["Changelog notes from the PR diff."],
        "not_relevant": ["A 1200-word blog post about our product launch."],
    }
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli", "prove"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=True,
    )
    data = json.loads(proc.stdout)
    assert data["via"] == "cli"
    families = {row["family"] for row in data["cases"]}
    assert families == {"wake", "output"}
    assert data["composite_0_100"] is None
    assert data["teachability_ok"] is True
    assert set(data["output_rubric"]) == set(RUBRIC_KEYS)
    output = [row for row in data["cases"] if row["family"] == "output"]
    assert all(row["rubric"] and set(row["rubric"]) >= set(RUBRIC_KEYS) for row in output)


def test_cli_rank_orders_by_score() -> None:
    ranked = run_rank(
        family="wake",
        job="Draft release notes from PR diffs for the changelog.",
        when="Release notes from a PR or changelog.",
        not_when="Marketing or blog posts.",
        prompts=[
            "Write a blog post about our product launch.",
            "Draft release notes from this PR diff for the changelog.",
        ],
    )
    assert ranked[0]["positive"] is True
    assert ranked[0]["score"] >= ranked[-1]["score"]
    assert all(item["family"] == "wake" for item in ranked)
