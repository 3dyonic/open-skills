"""Anthropic Academy Fluency 4Ds method cards.

UI card blurbs match Craft Ready Figma 1:16 (no invented chrome).
Quoted behavioral indicators come from the Academy fetch — never paraphrased.
"""

from __future__ import annotations

from typing import Any

ACADEMY_INDICATORS_URL = (
    "https://academy.claude.com/tutorials/the-4-ds-of-ai-fluency-behavioral-indicators"
)

DS = ("delegation", "description", "discernment", "diligence")

# Craft Ready frame 1:16 — card titles + blurbs. Do not invent alternate chrome.
METHOD_CARDS: tuple[dict[str, str], ...] = (
    {
        "id": "delegation",
        "name": "Delegation",
        "card": "What the agent owns vs what stays with you",
    },
    {
        "id": "description",
        "name": "Description",
        "card": "Plain job + when / not-when trigger craft",
    },
    {
        "id": "discernment",
        "name": "Discernment",
        "card": "Checks, near-misses, refuse paths",
    },
    {
        "id": "diligence",
        "name": "Diligence",
        "card": "Verify steps · more in references/",
    },
)

CITE_BAR = (
    "Cited: Anthropic Academy · Fluency 4Ds — Delegation · Description · "
    "Discernment · Diligence (cite only; no invented method prose)."
)


def methods_payload(quoted: dict[str, list[str]] | None = None) -> dict[str, Any]:
    quotes = quoted or {}
    cards = []
    for card in METHOD_CARDS:
        cards.append(
            {
                **card,
                "quoted_indicators": list(quotes.get(card["id"], [])),
            }
        )
    return {
        "citation": {
            "label": CITE_BAR,
            "url": ACADEMY_INDICATORS_URL,
        },
        "methods": cards,
    }


def method_name(method_id: str) -> str:
    for card in METHOD_CARDS:
        if card["id"] == method_id:
            return card["name"]
    raise KeyError(method_id)


def fill_order(first: str) -> list[str]:
    if first not in DS:
        raise ValueError(f"unknown method: {first}")
    rest = [d for d in DS if d != first]
    return [first, *rest]
