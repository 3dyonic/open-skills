"""Teachable wake benchmarks — show WHY, not pass/fail theater."""

from __future__ import annotations

import re
from typing import Any

_STOP = {
    "the",
    "a",
    "an",
    "to",
    "for",
    "of",
    "and",
    "or",
    "this",
    "that",
    "from",
    "with",
    "our",
    "you",
    "your",
    "me",
    "i",
    "we",
    "it",
    "in",
    "on",
    "at",
    "as",
    "is",
    "be",
    "do",
    "my",
    "about",
    "into",
    "over",
    "than",
    "then",
    "when",
    "not",
    "use",
    "ask",
    "asks",
    "someone",
    "please",
    "now",
    "job",
    "how",
    "what",
    "can",
    "could",
    "would",
    "should",
    "will",
    "just",
    "need",
}

_GENERIC = {
    "summarize",
    "summary",
    "write",
    "draft",
    "help",
    "create",
    "make",
    "explain",
    "describe",
}


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in _STOP and len(w) > 1}


def _preview(text: str, limit: int = 72) -> str:
    flat = " ".join((text or "").split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1] + "…"


def decide_wake(prompt: str, when: str, not_when: str, job: str) -> tuple[bool, set[str], set[str]]:
    """Return (woke, when-hits, not-when-hits). Deterministic; no LLM."""
    prompt_toks = tokens(prompt)
    when_toks = tokens(when) | tokens(job)
    not_toks = tokens(not_when)
    wake_hits = prompt_toks & when_toks
    not_hits = prompt_toks & not_toks
    if not_hits and len(not_hits) >= max(1, len(wake_hits)):
        return False, wake_hits, not_hits
    if len(wake_hits) >= 2:
        return True, wake_hits, not_hits
    if len(wake_hits) == 1 and not not_hits:
        return True, wake_hits, not_hits
    # Vague wake line + shared generic verb → over-trigger (the teachable fail).
    if len(when_toks) < 3 and (prompt_toks & _GENERIC) and (when_toks & _GENERIC):
        return True, wake_hits, not_hits
    return False, wake_hits, not_hits


def evaluate_case(
    prompt: str,
    *,
    kind: str,
    when: str,
    not_when: str,
    job: str,
) -> dict[str, Any]:
    expected_wake = kind == "should"
    woke, wake_hits, not_hits = decide_wake(prompt, when, not_when, job)
    passed = woke == expected_wake

    if expected_wake and woke:
        badge = "SHOULD WAKE"
        verdict = "Woke · matched"
        why = (
            f"WHY: wake line names the job ({_preview(job)}) + when "
            f"({_preview(when)})."
        )
        teach = "Keep this sharpness. Add a near-miss should-not next."
    elif (not expected_wake) and (not woke):
        badge = "SHOULD NOT"
        verdict = "Did not wake · good"
        why = f"WHY: not-when excludes this near-miss ({_preview(not_when)})."
        teach = "If it had woken: tighten not-when — name the off-jobs explicitly."
    elif expected_wake and not woke:
        badge = "FAILED · TEACH"
        verdict = "Did not wake · missed"
        why = (
            "WHY: the prompt did not match When — the wake line may be too narrow, "
            "or this should-case is off-job."
        )
        teach = "Change: name the unit + when explicitly, or fix the should prompt."
    else:
        badge = "FAILED · TEACH"
        verdict = "Woke · wrong job"
        why = "WHY: description too vague — overlapping verbs fire on the wrong job."
        teach = "Change: name the unit (the real job) + when/not-when explicitly."

    return {
        "prompt": prompt,
        "kind": kind,
        "woke": woke,
        "expected_wake": expected_wake,
        "passed": passed,
        "badge": badge,
        "verdict": verdict,
        "why": why,
        "teach": teach,
        "wake_hits": sorted(wake_hits),
        "not_hits": sorted(not_hits),
    }


def evaluate_benchmarks(
    *,
    job: str,
    when: str,
    not_when: str,
    should: list[str],
    should_not: list[str],
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for prompt in should:
        cases.append(evaluate_case(prompt, kind="should", when=when, not_when=not_when, job=job))
    for prompt in should_not:
        cases.append(evaluate_case(prompt, kind="should_not", when=when, not_when=not_when, job=job))
    return cases
