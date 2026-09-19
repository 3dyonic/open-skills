"""Thin rank/prove CLI. UI Run check shells out here — not an in-app eval suite.

Scores both:
  wake   — should / should-not
  output — relevant / not

External LLM may judge relevance text; this process always structures the score.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from app.external_llm import anthropic_text
from app.scheme import (
    CaseResult,
    ProveRequest,
    ProveResponse,
    RankItem,
    RankRequest,
    RankResponse,
)

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
    "here",
    "are",
    "results",
    "following",
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


def _score(sample: str, when: str, not_when: str, job: str) -> tuple[bool, float, set[str], set[str]]:
    sample_toks = tokens(sample)
    pos = tokens(when) | tokens(job)
    neg = tokens(not_when)
    pos_hits = sample_toks & pos
    neg_hits = sample_toks & neg
    score = float(len(pos_hits) - len(neg_hits))
    if neg_hits and len(neg_hits) >= max(1, len(pos_hits)):
        return False, score, pos_hits, neg_hits
    if len(pos_hits) >= 2:
        return True, score, pos_hits, neg_hits
    if len(pos_hits) == 1 and not neg_hits:
        return True, score, pos_hits, neg_hits
    if len(pos) < 3 and (sample_toks & _GENERIC) and (pos & _GENERIC):
        return True, score, pos_hits, neg_hits
    return False, score, pos_hits, neg_hits


def _llm_relevance(job: str, when: str, not_when: str, sample: str) -> tuple[bool, str] | None:
    prompt = (
        "Judge whether this skill OUTPUT is relevant to the job. JSON only:\n"
        '{"relevant":true,"why":"..."}\n'
        f"Job: {job}\nWhen: {when}\nNot when: {not_when}\nOutput:\n{sample}\n"
    )
    text = anthropic_text(prompt, max_tokens=200)
    if not text:
        return None
    try:
        start = text.find("{")
        end = text.rfind("}")
        data: dict[str, Any] = json.loads(text[start : end + 1])
        relevant = bool(data.get("relevant"))
        why = str(data.get("why") or "").strip()
        if why:
            if not why.upper().startswith("WHY"):
                why = f"WHY: {why}"
            return relevant, why
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    return None


def score_wake(prompt: str, kind: str, req: ProveRequest) -> CaseResult:
    expected = kind == "should"
    woke, score, pos_hits, _neg = _score(prompt, req.when, req.not_when, req.job)
    passed = woke == expected
    if expected and woke:
        badge, verdict = "SHOULD WAKE", "Woke · matched"
        why = f"WHY: wake line names the job ({_preview(req.job)}) + when ({_preview(req.when)})."
        teach = "Keep this sharpness. Add a near-miss should-not next."
    elif (not expected) and (not woke):
        badge, verdict = "SHOULD NOT", "Did not wake · good"
        why = f"WHY: not-when excludes this near-miss ({_preview(req.not_when)})."
        teach = "If it had woken: tighten not-when — name the off-jobs explicitly."
    elif expected and not woke:
        badge, verdict = "FAILED · TEACH", "Did not wake · missed"
        why = "WHY: the prompt did not match When — the wake line may be too narrow, or this should-case is off-job."
        teach = "Change: name the unit + when explicitly, or fix the should prompt."
    else:
        badge, verdict = "FAILED · TEACH", "Woke · wrong job"
        why = "WHY: description too vague — overlapping verbs fire on the wrong job."
        teach = "Change: name the unit (the real job) + when/not-when explicitly."
    return CaseResult(
        family="wake",
        prompt=prompt,
        kind=kind,
        woke=woke,
        relevant=False,
        expected=expected,
        passed=passed,
        badge=badge,
        verdict=verdict,
        why=why,
        teach=teach,
        score=score,
        hits=sorted(pos_hits),
    )


def score_output(sample: str, kind: str, req: ProveRequest) -> CaseResult:
    expected = kind == "relevant"
    judged = _llm_relevance(req.job, req.when, req.not_when, sample)
    if judged is not None:
        is_rel, why = judged
        score = 1.0 if is_rel else 0.0
        hits: set[str] = set()
    else:
        is_rel, score, hits, _neg = _score(sample, req.when, req.not_when, req.job)
        why = ""
    passed = is_rel == expected
    if expected and is_rel:
        badge, verdict = "RELEVANT", "On-job · matched"
        why = why or f"WHY: output stays on the job ({_preview(req.job)})."
        teach = "Keep the body on the unit. Depth goes in references/."
    elif (not expected) and (not is_rel):
        badge, verdict = "NOT RELEVANT", "Off-job · good"
        why = why or f"WHY: output is outside When ({_preview(req.not_when)})."
        teach = "If this had scored relevant: tighten not-when or the sample."
    elif expected and not is_rel:
        badge, verdict = "FAILED · TEACH", "Off-job · missed"
        why = why or "WHY: the sample does not look like this job's output."
        teach = "Change: make the relevant sample name the unit, or fix When."
    else:
        badge, verdict = "FAILED · TEACH", "On-job · wrong unit"
        why = why or "WHY: a not-relevant sample still looks like the job — wake/output too vague."
        teach = "Change: name the unit so off-job output cannot pass."
    return CaseResult(
        family="output",
        prompt=sample,
        kind=kind,
        woke=False,
        relevant=is_rel,
        expected=expected,
        passed=passed,
        badge=badge,
        verdict=verdict,
        why=why,
        teach=teach,
        score=float(score),
        hits=sorted(hits),
    )


def run_prove(req: ProveRequest) -> ProveResponse:
    cases: list[CaseResult] = []
    for prompt in req.should:
        cases.append(score_wake(prompt, "should", req))
    for prompt in req.should_not:
        cases.append(score_wake(prompt, "should_not", req))
    for sample in req.relevant:
        cases.append(score_output(sample, "relevant", req))
    for sample in req.not_relevant:
        cases.append(score_output(sample, "not", req))
    return ProveResponse(cases=cases)


def run_rank(req: RankRequest) -> RankResponse:
    ranked: list[RankItem] = []
    for prompt in req.prompts:
        positive, score, hits, _neg = _score(prompt, req.when, req.not_when, req.job)
        note = "matches job/when" if positive else "near-miss or off-job"
        if hits:
            note = f"{note}: {', '.join(sorted(hits)[:6])}"
        ranked.append(
            RankItem(
                family=req.family,
                prompt=prompt,
                score=float(score),
                positive=positive,
                note=note,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return RankResponse(ranked=ranked)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="open-skills-cli", description="Thin rank/prove CLI")
    parser.add_argument("command", choices=("prove", "rank"))
    args = parser.parse_args(argv)
    raw = sys.stdin.read()
    if args.command == "prove":
        req = ProveRequest.model_validate_json(raw)
        out = run_prove(req)
    else:
        req_r = RankRequest.model_validate_json(raw)
        out = run_rank(req_r)
    sys.stdout.write(out.model_dump_json(indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
