"""Thin rank/prove CLI — OSK-23 shape. No keep/kill floors.

Wake: should / should-not / near-miss, multi-run trigger rates (± P/R), harness honesty.
Output: with / without + assertions/evidence; LLM judge = pass/fail + evidence.
ProveReport = {wake, output}. Evidence on every case.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from app.external_llm import anthropic_text
from app.scheme import (
    Evidence,
    OutputAssertion,
    OutputCase,
    OutputReport,
    ProveReport,
    ProveRequest,
    RankItem,
    RankRequest,
    WakeCase,
    WakeReport,
    rate,
)

_STOP = {
    "the", "a", "an", "to", "for", "of", "and", "or", "this", "that", "from",
    "with", "our", "you", "your", "me", "i", "we", "it", "in", "on", "at", "as",
    "is", "be", "do", "my", "about", "into", "over", "than", "then", "when",
    "not", "use", "ask", "asks", "someone", "please", "now", "job", "how",
    "what", "can", "could", "would", "should", "will", "just", "need", "here",
    "are", "results", "following",
}

_GENERIC = {
    "summarize", "summary", "write", "draft", "help", "create", "make",
    "explain", "describe",
}


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in _STOP and len(w) > 1}


def _preview(text: str, limit: int = 72) -> str:
    flat = " ".join((text or "").split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1] + "…"


def _why(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    return text if text.upper().startswith("WHY") else f"WHY: {text}"


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


def _llm_output_judge(sample: str, req: ProveRequest, kind: str) -> tuple[bool, str, str] | None:
    expect = "with the skill (on-job)" if kind == "with" else "without the skill (off-job / control)"
    prompt = (
        "Judge this OUTPUT fixture. JSON only:\n"
        '{"passed":true,"why":"...","quote":"span that justifies"}\n'
        f"Expected: {expect}\nJob: {req.job}\nWhen: {req.when}\nNot when: {req.not_when}\n"
        f"Steps: {req.body}\nOutput:\n{sample}\n"
    )
    text = anthropic_text(prompt, max_tokens=220)
    if not text:
        return None
    try:
        start = text.find("{")
        end = text.rfind("}")
        data: dict[str, Any] = json.loads(text[start : end + 1])
        why = str(data.get("why") or "").strip()
        if data.get("passed") is None or (not bool(data.get("passed")) and not why):
            return None
        return bool(data.get("passed")), _why(why), str(data.get("quote") or "")
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def score_wake(prompt: str, kind: str, req: ProveRequest) -> WakeCase:
    expected = kind == "should"
    woke_flags: list[bool] = []
    last_hits: set[str] = set()
    last_neg: set[str] = set()
    last_score = 0.0
    for _ in range(req.runs):
        woke, score, pos_hits, neg_hits = _score(prompt, req.when, req.not_when, req.job)
        woke_flags.append(woke)
        last_hits, last_neg, last_score = pos_hits, neg_hits, score
    woke_count = sum(1 for flag in woke_flags if flag)
    trigger_rate = woke_count / len(woke_flags)
    woke = woke_flags[-1]
    matched = woke == expected
    honest = len(set(woke_flags)) == 1
    against = req.when if expected else req.not_when
    if expected and woke:
        badge, verdict = "SHOULD", "Matched · woke"
        why = _why(f"wake line names the job ({_preview(req.job)}) + when ({_preview(req.when)}).")
    elif (not expected) and (not woke):
        badge = "SHOULD NOT" if kind == "should_not" else "NEAR-MISS"
        verdict = "Did not wake · good"
        why = _why(f"not-when excludes this near-miss ({_preview(req.not_when)}).")
    elif expected:
        badge, verdict = "MISMATCH", "Did not wake · missed"
        why = _why("the prompt did not match When — wake line may be too narrow, or this should-case is off-job.")
    else:
        badge, verdict = "MISMATCH", "Woke · wrong job"
        why = _why("description too vague — overlapping verbs fire on the wrong job.")
    return WakeCase(
        kind=kind,  # type: ignore[arg-type]
        prompt=prompt,
        woke=woke,
        expected_wake=expected,
        matched=matched,
        runs=req.runs,
        woke_count=woke_count,
        trigger_rate=round(trigger_rate, 4),
        harness_honest=honest,
        evidence=Evidence(
            fixture=prompt,
            quote=_preview(prompt),
            hits=sorted(last_hits | last_neg),
            against=against,
            source="harness",
            notes=f"runs={req.runs} woke_count={woke_count} token_score={last_score}",
        ),
        why=why,
        badge=badge,
        verdict=verdict,
    )


def score_output(sample: str, kind: str, req: ProveRequest) -> OutputCase:
    judged = _llm_output_judge(sample, req, kind)
    on_job, _score_n, hits, neg = _score(sample, req.when, req.not_when, req.job)
    if judged is not None:
        passed, why, quote = judged
        judge: str = "llm"
        source: str = "llm"
    else:
        passed = on_job if kind == "with" else (not on_job)
        quote = _preview(sample)
        judge = "deterministic"
        source = "deterministic"
        if kind == "with" and passed:
            why = _why(f"output stays on the job ({_preview(req.job)}).")
        elif kind == "without" and passed:
            why = _why(f"control output is outside When ({_preview(req.not_when)}).")
        elif kind == "with":
            why = _why("with-skill sample does not look on-job.")
        else:
            why = _why("without-skill control still looks on-job.")
    evidence = Evidence(
        fixture=sample,
        quote=quote or _preview(sample),
        hits=sorted(hits | neg),
        against=req.when if kind == "with" else req.not_when,
        source=source,  # type: ignore[arg-type]
        notes=f"kind={kind} judge={judge}",
    )
    assertion = OutputAssertion(
        name="on_job" if kind == "with" else "off_job_control",
        passed=passed,
        evidence=evidence,
        why="" if passed else why,
    )
    if kind == "with" and passed:
        badge, verdict = "WITH", "With skill · on-job"
    elif kind == "without" and passed:
        badge, verdict = "WITHOUT", "Without skill · control"
    else:
        badge, verdict = "MISMATCH", "Judge fail · see evidence"
    return OutputCase(
        kind=kind,  # type: ignore[arg-type]
        sample=sample,
        assertions=[assertion],
        judge=judge,  # type: ignore[arg-type]
        passed=passed,
        evidence=evidence,
        why=why,
        badge=badge,
        verdict=verdict,
    )


def build_wake(cases: list[WakeCase]) -> WakeReport:
    should = [c for c in cases if c.kind == "should"]
    negatives = [c for c in cases if c.kind in {"should_not", "near_miss"}]
    recall = rate(sum(1 for c in should if c.woke), len(should))
    precision = rate(sum(1 for c in negatives if not c.woke), len(negatives))
    rates: dict[str, float] = {}
    for kind in ("should", "should_not", "near_miss"):
        bucket = [c for c in cases if c.kind == kind]
        if bucket:
            rates[kind] = round(sum(c.trigger_rate for c in bucket) / len(bucket), 4)
    return WakeReport(
        cases=cases,
        trigger_rates=rates,
        recall=recall,
        precision=precision,
        harness_honesty=all(c.harness_honest for c in cases) if cases else True,
    )


def run_prove(req: ProveRequest) -> ProveReport:
    wake_cases: list[WakeCase] = []
    for prompt in req.should:
        wake_cases.append(score_wake(prompt, "should", req))
    for prompt in req.should_not:
        wake_cases.append(score_wake(prompt, "should_not", req))
    for prompt in req.near_miss:
        wake_cases.append(score_wake(prompt, "near_miss", req))
    output_cases: list[OutputCase] = []
    for sample in req.output_with():
        output_cases.append(score_output(sample, "with", req))
    for sample in req.output_without():
        output_cases.append(score_output(sample, "without", req))
    return ProveReport(wake=build_wake(wake_cases), output=OutputReport(cases=output_cases))


def run_rank(req: RankRequest) -> ProveReport:
    prove_req = ProveRequest(
        job=req.job,
        when=req.when,
        not_when=req.not_when,
        body=req.body,
        runs=req.runs,
    )
    ranked: list[RankItem] = []
    wake_cases: list[WakeCase] = []
    output_cases: list[OutputCase] = []
    for prompt in req.prompts:
        if req.family == "output":
            case = score_output(prompt, "with", prove_req)
            output_cases.append(case)
            ranked.append(
                RankItem(
                    family="output",
                    prompt=prompt,
                    score=1.0 if case.passed else 0.0,
                    positive=case.passed,
                    note=case.verdict,
                    evidence=case.evidence,
                )
            )
        else:
            case_w = score_wake(prompt, "should", prove_req)
            wake_cases.append(case_w)
            ranked.append(
                RankItem(
                    family="wake",
                    prompt=prompt,
                    score=case_w.trigger_rate,
                    positive=case_w.woke,
                    note=case_w.verdict,
                    evidence=case_w.evidence,
                )
            )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ProveReport(wake=build_wake(wake_cases), output=OutputReport(cases=output_cases), ranked=ranked)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="open-skills-cli", description="Thin rank/prove CLI")
    parser.add_argument("command", choices=("prove", "rank"))
    args = parser.parse_args(argv)
    raw = sys.stdin.read()
    if args.command == "prove":
        out = run_prove(ProveRequest.model_validate_json(raw))
    else:
        out = run_rank(RankRequest.model_validate_json(raw))
    sys.stdout.write(out.model_dump_json(indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
