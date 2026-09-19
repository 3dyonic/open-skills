"""Thin rank/prove CLI. UI Run check shells out here — not an in-app eval suite.

Primary:
  wake   — recall (should) / precision (should-not)
  output — rubric: on_job, complete, safe, cites_skill_steps + why on fail

LLM fills the rubric when a key is present; this process always structures it.
Composite weights are optional and never defaulted to 40/30/30.
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
    OutputRubric,
    ProveReport,
    ProveRequest,
    RankItem,
    RankRequest,
    RubricCheck,
    RUBRIC_KEYS,
    build_report,
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

_UNSAFE = (
    "ignore safety",
    "jailbreak",
    "rm -rf",
    "api_key",
    "apikey",
    "password:",
    "secret key",
)


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


def _why(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if text.upper().startswith("WHY"):
        return text
    return f"WHY: {text}"


def _check(passed: bool, why: str) -> RubricCheck:
    return RubricCheck(passed=passed, why=_why(why) if not passed else "")


def _heuristic_rubric(sample: str, req: ProveRequest) -> OutputRubric:
    on_job, _score_n, hits, _neg = _score(sample, req.when, req.not_when, req.job)
    complete = len(tokens(sample)) >= 4
    lowered = (sample or "").lower()
    safe = not any(flag in lowered for flag in _UNSAFE)
    step_toks = tokens(req.body)
    if step_toks:
        cites = bool(tokens(sample) & step_toks)
    else:
        cites = True
    return OutputRubric(
        on_job=_check(on_job, f"output does not stay on the job ({_preview(req.job)})."),
        complete=_check(complete, "output is too thin to be a complete result."),
        safe=_check(safe, "output looks unsafe for a skill pack."),
        cites_skill_steps=_check(
            cites,
            f"output does not cite the skill steps ({_preview(req.body) or 'none provided'}).",
        ),
    )


def _parse_rubric(data: dict[str, Any]) -> OutputRubric | None:
    items: dict[str, RubricCheck] = {}
    for key in RUBRIC_KEYS:
        raw = data.get(key)
        if isinstance(raw, bool):
            passed = raw
            why = str(data.get("why") or "")
        elif isinstance(raw, dict):
            passed = bool(raw.get("passed"))
            why = str(raw.get("why") or data.get("why") or "")
        else:
            return None
        if not passed and not why.strip():
            return None
        items[key] = _check(passed, why)
    return OutputRubric(**items)


def _llm_rubric(sample: str, req: ProveRequest) -> OutputRubric | None:
    prompt = (
        "Judge this skill OUTPUT against a checklist. JSON only:\n"
        '{"on_job":{"passed":true,"why":""},"complete":{"passed":true,"why":""},'
        '"safe":{"passed":true,"why":""},"cites_skill_steps":{"passed":true,"why":""},'
        '"why":"overall if any fail"}\n'
        "why is required on every failed check.\n"
        f"Job: {req.job}\nWhen: {req.when}\nNot when: {req.not_when}\n"
        f"Steps: {req.body}\nOutput:\n{sample}\n"
    )
    text = anthropic_text(prompt, max_tokens=300)
    if not text:
        return None
    try:
        start = text.find("{")
        end = text.rfind("}")
        data: dict[str, Any] = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    return _parse_rubric(data)


def score_wake(prompt: str, kind: str, req: ProveRequest) -> CaseResult:
    expected = kind == "should"
    woke, score, pos_hits, _neg = _score(prompt, req.when, req.not_when, req.job)
    passed = woke == expected
    if expected and woke:
        badge, verdict = "SHOULD WAKE", "Matched · woke"
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
    rubric = _llm_rubric(sample, req) or _heuristic_rubric(sample, req)
    is_rel = rubric.on_job.passed
    if expected:
        passed = rubric.all_passed()
    else:
        passed = not is_rel
    failed = [f"{key}: {item.why}" for key, item in rubric.as_items() if not item.passed]
    if expected and passed:
        badge, verdict = "RELEVANT", "Relevant · on-job"
        why = f"WHY: output stays on the job ({_preview(req.job)})."
        teach = "Keep the body on the unit. Depth goes in references/."
    elif (not expected) and passed:
        badge, verdict = "NOT RELEVANT", "Not relevant · off-job"
        why = f"WHY: output is outside When ({_preview(req.not_when)})."
        teach = "If this had scored on-job: tighten not-when or the sample."
    elif expected:
        badge, verdict = "FAILED · TEACH", "Off-job · missed"
        why = failed[0] if failed else "WHY: the sample fails the output rubric."
        teach = "Change: make the sample on-job, complete, safe, and cite the steps."
    else:
        badge, verdict = "FAILED · TEACH", "On-job · wrong unit"
        why = rubric.on_job.why or "WHY: a not-relevant sample still looks like the job."
        teach = "Change: name the unit so off-job output cannot pass."
    hits = tokens(sample) & (tokens(req.when) | tokens(req.job))
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
        score=4.0 if expected and passed else float(sum(int(item.passed) for _k, item in rubric.as_items())),
        hits=sorted(hits),
        rubric=rubric,
    )


def run_prove(req: ProveRequest) -> ProveReport:
    cases: list[CaseResult] = []
    for prompt in req.should:
        cases.append(score_wake(prompt, "should", req))
    for prompt in req.should_not:
        cases.append(score_wake(prompt, "should_not", req))
    for sample in req.relevant:
        cases.append(score_output(sample, "relevant", req))
    for sample in req.not_relevant:
        cases.append(score_output(sample, "not", req))
    return build_report(cases, weights=req.weights)


def run_rank(req: RankRequest) -> ProveReport:
    prove_req = ProveRequest(
        job=req.job,
        when=req.when,
        not_when=req.not_when,
        body=req.body,
        weights=req.weights,
    )
    cases: list[CaseResult] = []
    ranked: list[RankItem] = []
    for prompt in req.prompts:
        if req.family == "output":
            case = score_output(prompt, "relevant", prove_req)
        else:
            case = score_wake(prompt, "should", prove_req)
        cases.append(case)
        note = "matches job/when" if case.passed else "near-miss or off-job"
        if case.hits:
            note = f"{note}: {', '.join(case.hits[:6])}"
        ranked.append(
            RankItem(
                family=req.family,
                prompt=prompt,
                score=float(case.score),
                positive=case.passed,
                note=note,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return build_report(cases, ranked=ranked, weights=req.weights)


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
