"""Pydantic scheme for rank/prove CLI.

Primary surface (Day-1):
  Wake — recall (should) / precision (should-not)
  Output — rubric checklist: on_job, complete, safe, cites_skill_steps
  why required on every failure (teachability_ok gate, not a weight)

Composite 0–100 is optional/secondary. Weights are NOT an Eng lock —
40/30/30 was challenged and is not acceptance. Pass `weights` on the
request only if a later stamp asks the CLI to emit a secondary composite.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Family = Literal["wake", "output"]
WakeKind = Literal["should", "should_not"]
OutputKind = Literal["relevant", "not"]
RubricKey = Literal["on_job", "complete", "safe", "cites_skill_steps"]
WakeCheckName = Literal["wake_recall", "wake_precision"]
CheckName = Literal["wake_recall", "wake_precision", "on_job", "complete", "safe", "cites_skill_steps"]

RUBRIC_KEYS: tuple[RubricKey, ...] = ("on_job", "complete", "safe", "cites_skill_steps")


class ProveRequest(BaseModel):
    job: str
    when: str
    not_when: str
    body: str = ""
    should: list[str] = Field(default_factory=list)
    should_not: list[str] = Field(default_factory=list)
    relevant: list[str] = Field(default_factory=list)
    not_relevant: list[str] = Field(default_factory=list)
    weights: dict[str, int] | None = None


class RubricCheck(BaseModel):
    passed: bool
    why: str = ""

    @model_validator(mode="after")
    def why_required_on_fail(self) -> RubricCheck:
        if not self.passed and not (self.why or "").strip():
            raise ValueError("why is required on every rubric failure")
        return self


class OutputRubric(BaseModel):
    on_job: RubricCheck
    complete: RubricCheck
    safe: RubricCheck
    cites_skill_steps: RubricCheck

    def as_items(self) -> list[tuple[RubricKey, RubricCheck]]:
        return [(key, getattr(self, key)) for key in RUBRIC_KEYS]

    def all_passed(self) -> bool:
        return all(item.passed for _key, item in self.as_items())


class CaseResult(BaseModel):
    family: Family
    prompt: str
    kind: str
    woke: bool = False
    relevant: bool = False
    expected: bool
    passed: bool
    badge: str
    verdict: str
    why: str
    teach: str
    score: float = 0.0
    hits: list[str] = Field(default_factory=list)
    rubric: OutputRubric | None = None

    @model_validator(mode="after")
    def why_required_on_failure(self) -> CaseResult:
        if not self.passed and not (self.why or "").strip():
            raise ValueError("why is required on every failure")
        return self


class FailureWhy(BaseModel):
    family: Family
    kind: str
    prompt: str
    why: str = Field(min_length=1)
    check: CheckName


class VerticalScore(BaseModel):
    """Checklist bucket. `weight` is optional and never required for acceptance."""

    name: str
    passed: int = 0
    total: int = 0
    score_0_100: float | None = None
    weight: int | None = None


class RankRequest(BaseModel):
    family: Family = "wake"
    job: str
    when: str
    not_when: str
    body: str = ""
    prompts: list[str] = Field(default_factory=list)
    weights: dict[str, int] | None = None


class RankItem(BaseModel):
    family: Family
    prompt: str
    score: float
    positive: bool
    note: str


class ProveReport(BaseModel):
    cases: list[CaseResult]
    failures: list[FailureWhy] = Field(default_factory=list)
    wake_recall: VerticalScore
    wake_precision: VerticalScore
    output_rubric: dict[str, VerticalScore]
    teachability_ok: bool
    composite_0_100: float | None = None
    ranked: list[RankItem] = Field(default_factory=list)
    via: Literal["cli"] = "cli"


def check_for_wake(kind: str) -> WakeCheckName:
    return "wake_recall" if kind == "should" else "wake_precision"


def bucket(name: str, passed: int, total: int, weight: int | None = None) -> VerticalScore:
    pct = (100.0 * passed / total) if total else None
    return VerticalScore(
        name=name,
        passed=passed,
        total=total,
        score_0_100=round(pct, 2) if pct is not None else None,
        weight=weight,
    )


def optional_composite(
    scores: list[VerticalScore],
    weights: dict[str, int] | None,
) -> float | None:
    """Secondary only. No default weights — omit unless a stamp supplies them."""
    if not weights:
        return None
    num = 0.0
    den = 0
    by_name = {row.name: row for row in scores}
    for name, weight in weights.items():
        row = by_name.get(name)
        if row is None or row.score_0_100 is None or weight <= 0:
            continue
        num += row.score_0_100 * weight
        den += weight
    if not den:
        return None
    return round(num / den, 2)


def build_report(
    cases: list[CaseResult],
    ranked: list[RankItem] | None = None,
    weights: dict[str, int] | None = None,
) -> ProveReport:
    teachability_ok = True
    failures: list[FailureWhy] = []

    def add_failure(case: CaseResult, check: CheckName, why: str) -> None:
        nonlocal teachability_ok
        text = (why or "").strip()
        if not text:
            teachability_ok = False
            text = "WHY: failure reason missing."
        failures.append(
            FailureWhy(
                family=case.family,
                kind=case.kind,
                prompt=case.prompt,
                why=text,
                check=check,
            )
        )

    recall_p = recall_t = 0
    prec_p = prec_t = 0
    rubric_counts = {key: [0, 0] for key in RUBRIC_KEYS}

    for case in cases:
        if case.family == "wake":
            if case.kind == "should":
                recall_t += 1
                recall_p += int(case.passed)
                if not case.passed:
                    add_failure(case, "wake_recall", case.why)
            else:
                prec_t += 1
                prec_p += int(case.passed)
                if not case.passed:
                    add_failure(case, "wake_precision", case.why)
            continue
        if case.rubric is None:
            if not case.passed:
                add_failure(case, "on_job", case.why)
            continue
        for key, item in case.rubric.as_items():
            rubric_counts[key][1] += 1
            rubric_counts[key][0] += int(item.passed)
            if not item.passed:
                add_failure(case, key, item.why)

    wake_recall = bucket("wake_recall", recall_p, recall_t)
    wake_precision = bucket("wake_precision", prec_p, prec_t)
    output_rubric = {
        key: bucket(key, passed, total) for key, (passed, total) in rubric_counts.items()
    }
    scores = [wake_recall, wake_precision, *output_rubric.values()]
    return ProveReport(
        cases=cases,
        failures=failures,
        wake_recall=wake_recall,
        wake_precision=wake_precision,
        output_rubric=output_rubric,
        teachability_ok=teachability_ok,
        composite_0_100=optional_composite(scores, weights),
        ranked=list(ranked or []),
    )
