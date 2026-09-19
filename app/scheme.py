"""Pydantic scheme for the rank/prove CLI — wake + output relevance."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Family = Literal["wake", "output"]
WakeKind = Literal["should", "should_not"]
OutputKind = Literal["relevant", "not"]


class ProveRequest(BaseModel):
    job: str
    when: str
    not_when: str
    should: list[str] = Field(default_factory=list)
    should_not: list[str] = Field(default_factory=list)
    relevant: list[str] = Field(default_factory=list)
    not_relevant: list[str] = Field(default_factory=list)


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


class ProveResponse(BaseModel):
    cases: list[CaseResult]
    via: Literal["cli"] = "cli"


class RankRequest(BaseModel):
    family: Family = "wake"
    job: str
    when: str
    not_when: str
    prompts: list[str] = Field(default_factory=list)


class RankItem(BaseModel):
    family: Family
    prompt: str
    score: float
    positive: bool
    note: str


class RankResponse(BaseModel):
    ranked: list[RankItem]
    via: Literal["cli"] = "cli"
