"""OSK-23 prove shape. OSK-22 Day-1: no numeric keep/kill floors.

ProveReport = {wake, output}. Evidence on every case. No required composite %.
Optional floors later only if labeled ours — this module does not invent them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Family = Literal["wake", "output"]
WakeKind = Literal["should", "should_not", "near_miss"]
OutputKind = Literal["with", "without"]
Judge = Literal["deterministic", "llm"]
EvidenceSource = Literal["deterministic", "llm", "harness"]


class Evidence(BaseModel):
    """Ties a judgment to a visible fixture — not a bare pass/fail or number."""

    fixture: str
    quote: str = ""
    hits: list[str] = Field(default_factory=list)
    against: str = ""
    source: EvidenceSource = "deterministic"
    notes: str = ""


class ProveRequest(BaseModel):
    job: str
    when: str
    not_when: str
    body: str = ""
    should: list[str] = Field(default_factory=list)
    should_not: list[str] = Field(default_factory=list)
    near_miss: list[str] = Field(default_factory=list)
    with_skill: list[str] = Field(default_factory=list)
    without_skill: list[str] = Field(default_factory=list)
    relevant: list[str] = Field(default_factory=list)
    not_relevant: list[str] = Field(default_factory=list)
    runs: int = Field(default=1, ge=1, le=32)

    def output_with(self) -> list[str]:
        return list(self.with_skill or self.relevant)

    def output_without(self) -> list[str]:
        return list(self.without_skill or self.not_relevant)


class WakeCase(BaseModel):
    family: Literal["wake"] = "wake"
    kind: WakeKind
    prompt: str
    woke: bool
    expected_wake: bool
    matched: bool
    runs: int = 1
    woke_count: int = 0
    trigger_rate: float
    harness_honest: bool
    evidence: Evidence
    why: str
    badge: str = ""
    verdict: str = ""

    @model_validator(mode="after")
    def evidence_and_why(self) -> WakeCase:
        if not (self.evidence.fixture or "").strip():
            raise ValueError("evidence.fixture is required on every wake case")
        if not self.matched and not (self.why or "").strip():
            raise ValueError("why is required on every wake mismatch")
        return self


class WakeReport(BaseModel):
    cases: list[WakeCase]
    trigger_rates: dict[str, float] = Field(default_factory=dict)
    recall: float | None = None
    precision: float | None = None
    harness_honesty: bool = True


class OutputAssertion(BaseModel):
    name: str
    passed: bool
    evidence: Evidence
    why: str = ""

    @model_validator(mode="after")
    def why_on_fail(self) -> OutputAssertion:
        if not self.passed and not (self.why or "").strip():
            raise ValueError("why is required on every failed assertion")
        return self


class OutputCase(BaseModel):
    family: Literal["output"] = "output"
    kind: OutputKind
    sample: str
    assertions: list[OutputAssertion] = Field(default_factory=list)
    judge: Judge
    passed: bool
    evidence: Evidence
    why: str
    badge: str = ""
    verdict: str = ""

    @model_validator(mode="after")
    def evidence_and_why(self) -> OutputCase:
        if not (self.evidence.fixture or "").strip():
            raise ValueError("evidence.fixture is required on every output case")
        if not self.passed and not (self.why or "").strip():
            raise ValueError("why is required on every output fail")
        return self


class OutputReport(BaseModel):
    cases: list[OutputCase]


class RankRequest(BaseModel):
    family: Family = "wake"
    job: str
    when: str
    not_when: str
    body: str = ""
    prompts: list[str] = Field(default_factory=list)
    runs: int = Field(default=1, ge=1, le=32)


class RankItem(BaseModel):
    family: Family
    prompt: str
    score: float
    positive: bool
    note: str
    evidence: Evidence


class ProveReport(BaseModel):
    wake: WakeReport
    output: OutputReport
    via: Literal["cli"] = "cli"
    ranked: list[RankItem] = Field(default_factory=list)


def rate(passed: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round(passed / total, 4)
