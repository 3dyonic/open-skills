"""Fetch Anthropic Academy 4Ds behavioral indicators and quote them.

Source of truth:
https://academy.claude.com/tutorials/the-4-ds-of-ai-fluency-behavioral-indicators

No paraphrase invent. If the live page only yields the prerendered intro
(the indicator widget is JS-hydrated), we return that excerpt plus the cite
URL — we do not fill gaps with third-party lists.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.methods import ACADEMY_INDICATORS_URL, DS

USER_AGENT = "open-skills-osk-16/0.1 (+https://github.com/3dyonic/open-skills)"

_D_HEADING = re.compile(
    r"^(delegation|description|discernment|diligence)\b",
    re.IGNORECASE,
)


@dataclass
class AcademyCite:
    url: str
    title: str
    fetched: bool
    excerpt: str
    quotes: dict[str, list[str]] = field(default_factory=dict)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "fetched": self.fetched,
            "excerpt": self.excerpt,
            "quotes": self.quotes,
            "error": self.error,
        }


def _strip_tags(raw: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|li|h1|h2|h3|h4|tr|section)>", "\n", text)
    text = re.sub(r"(?is)<li[^>]*>", "\n- ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_quotes(html: str) -> tuple[str, str, dict[str, list[str]]]:
    """Parse fetched Academy HTML. Quote only what the page says."""
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = html_lib.unescape(re.sub(r"<[^>]+>", "", title_m.group(1))).strip() if title_m else ""
    title = title.split("·")[0].strip() or "The 4 Ds of AI Fluency — Behavioral Indicators"

    text = _strip_tags(html)
    quotes: dict[str, list[str]] = {d: [] for d in DS}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip(" \t-•")
        if not line:
            continue
        heading = _D_HEADING.match(line)
        if heading and len(line) < 40:
            current = heading.group(1).lower()
            continue
        if current and 8 <= len(line) <= 220:
            if line.lower() in DS:
                continue
            if line not in quotes[current]:
                quotes[current].append(line)
    # Keep only Ds that actually yielded quotes.
    quotes = {k: v for k, v in quotes.items() if v}

    # Quote a page sentence/paragraph — prefer the tutorial lede, never invent.
    flat = " ".join(text.split())
    excerpt = ""
    lede = re.search(
        r"This tutorial offers a full list of the AI fluency behaviors cited in the Anthropic Education Report\.[^.]*\.",
        flat,
    )
    if lede:
        excerpt = lede.group(0).strip()[:600]
    else:
        hit = re.search(r".{0,40}full list of the AI fluency behaviors.{0,400}", flat)
        excerpt = hit.group(0).strip()[:600] if hit else flat[:600]
    return title, excerpt, quotes


def parse_academy_html(html: str, *, url: str = ACADEMY_INDICATORS_URL) -> AcademyCite:
    title, excerpt, quotes = extract_quotes(html)
    return AcademyCite(
        url=url,
        title=title,
        fetched=True,
        excerpt=excerpt,
        quotes=quotes,
    )


def fetch_academy_indicators(
    *,
    client: httpx.Client | None = None,
    timeout: float = 15.0,
) -> AcademyCite:
    own = client is None
    http = client or httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    try:
        response = http.get(ACADEMY_INDICATORS_URL)
        response.raise_for_status()
        return parse_academy_html(response.text, url=str(response.url))
    except Exception as exc:  # noqa: BLE001 — surface fetch failure, do not invent quotes
        return AcademyCite(
            url=ACADEMY_INDICATORS_URL,
            title="The 4 Ds of AI Fluency — Behavioral Indicators",
            fetched=False,
            excerpt="",
            quotes={},
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if own:
            http.close()


def quoted_for_d(cite: AcademyCite, method_id: str) -> list[str]:
    return list(cite.quotes.get(method_id, []))
