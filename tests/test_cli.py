import json
import subprocess
import sys
from pathlib import Path

from app.prove import run_rank

ROOT = Path(__file__).resolve().parents[1]


def test_cli_prove_subprocess() -> None:
    payload = {
        "job": "Draft release notes from PR diffs for the changelog.",
        "when": "Release notes from a PR or changelog.",
        "not_when": "Marketing or blog posts.",
        "body": "Draft the notes from the PR diff.",
        "should": ["Draft release notes from this PR diff for the changelog."],
        "should_not": ["Write a blog post about our product launch."],
        "near_miss": ["Summarize this meeting for the team."],
        "with_skill": ["Changelog notes from the PR diff."],
        "without_skill": ["A 1200-word blog post about our product launch."],
        "runs": 3,
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
    assert "wake" in data and "output" in data
    assert "composite_0_100" not in data
    assert data["wake"]["cases"][0]["runs"] == 3
    assert data["wake"]["cases"][0]["evidence"]["fixture"]
    assert data["output"]["cases"][0]["judge"] in {"deterministic", "llm"}
    assert data["output"]["cases"][0]["assertions"]


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
    assert all(item["evidence"]["fixture"] for item in ranked)
