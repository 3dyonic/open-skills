from pathlib import Path

from app.academy import ACADEMY_INDICATORS_URL, fetch_academy_indicators, parse_academy_html
from app.methods import ACADEMY_INDICATORS_URL as METHODS_URL
from app.methods import CITE_BAR, methods_payload


FIXTURE = Path(__file__).parent / "fixtures" / "academy_indicators.html"


def test_methods_cite_academy_url() -> None:
    payload = methods_payload()
    assert payload["citation"]["url"] == "https://academy.claude.com/tutorials/the-4-ds-of-ai-fluency-behavioral-indicators"
    assert payload["citation"]["url"] == METHODS_URL == ACADEMY_INDICATORS_URL
    assert "no invented method prose" in CITE_BAR
    ids = [m["id"] for m in payload["methods"]]
    assert ids == ["delegation", "description", "discernment", "diligence"]


def test_excerpt_prefers_tutorial_lede_not_nav() -> None:
    html = """
    <title>The 4 Ds of AI Fluency — Behavioral Indicators · Claude Academy</title>
    <nav>/ Tutorials</nav>
    <p>This tutorial offers a full list of the AI fluency behaviors cited in the Anthropic Education Report. It's a quick reference.</p>
    """
    cite = parse_academy_html(html)
    assert cite.excerpt.startswith("This tutorial offers a full list of the AI fluency behaviors")
    assert not cite.excerpt.startswith("/ Tutorials")


def test_parse_quotes_indicators_from_fetched_html() -> None:
    cite = parse_academy_html(FIXTURE.read_text(encoding="utf-8"))
    assert cite.fetched
    assert "Clarifies goal before asking for help" in cite.quotes["delegation"]
    assert "Specifies format and structure needed" in cite.quotes["description"]
    assert "Checks facts and claims that matter" in cite.quotes["discernment"]
    assert "Verifies and tests outputs before sharing" in cite.quotes["diligence"]
    assert "Anthropic Education Report" in cite.excerpt


def test_fetch_does_not_invent_on_failure(monkeypatch) -> None:
    import httpx

    def boom(*_a, **_k):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.Client, "get", boom)
    cite = fetch_academy_indicators()
    assert cite.fetched is False
    assert cite.quotes == {}
    assert cite.url == ACADEMY_INDICATORS_URL
    assert cite.error
