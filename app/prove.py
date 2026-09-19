"""Shell out to the rank/prove CLI. No in-app eval suite. No keep/kill floors."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.scheme import ProveReport, ProveRequest, RankRequest

ROOT = Path(__file__).resolve().parent.parent


class ProveCLIError(RuntimeError):
    def __init__(self, message: str, *, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr


def _run(command: str, payload: dict[str, Any]) -> dict[str, Any]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    parts = [str(ROOT)]
    if pythonpath:
        parts.append(pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli", command],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise ProveCLIError(
            f"CLI {command} failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}",
            stderr=proc.stderr,
        )
    data = json.loads(proc.stdout)
    if data.get("via") != "cli":
        raise ProveCLIError("CLI response missing via=cli")
    if "wake" not in data or "output" not in data:
        raise ProveCLIError("CLI response missing wake/output")
    return data


def flatten_cases(report: ProveReport) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in report.wake.cases:
        row = case.model_dump()
        row["passed"] = case.matched
        rows.append(row)
    for case in report.output.cases:
        row = case.model_dump()
        row["prompt"] = case.sample
        rows.append(row)
    return rows


def run_prove(
    *,
    job: str,
    when: str,
    not_when: str,
    should: list[str],
    should_not: list[str],
    near_miss: list[str] | None = None,
    relevant: list[str] | None = None,
    not_relevant: list[str] | None = None,
    with_skill: list[str] | None = None,
    without_skill: list[str] | None = None,
    body: str = "",
    runs: int = 1,
) -> ProveReport:
    req = ProveRequest(
        job=job,
        when=when,
        not_when=not_when,
        body=body,
        should=should,
        should_not=should_not,
        near_miss=near_miss or [],
        with_skill=with_skill or [],
        without_skill=without_skill or [],
        relevant=relevant or [],
        not_relevant=not_relevant or [],
        runs=runs,
    )
    data = _run("prove", req.model_dump())
    return ProveReport.model_validate(data)


def run_rank(
    *,
    family: str,
    job: str,
    when: str,
    not_when: str,
    prompts: list[str],
    body: str = "",
    runs: int = 1,
) -> list[dict[str, Any]]:
    req = RankRequest(
        family=family,  # type: ignore[arg-type]
        job=job,
        when=when,
        not_when=not_when,
        body=body,
        prompts=prompts,
        runs=runs,
    )
    data = _run("rank", req.model_dump())
    report = ProveReport.model_validate(data)
    return [row.model_dump() for row in report.ranked]
