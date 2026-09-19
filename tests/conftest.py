from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import academy as academy_mod
from app import main as main_mod
from app.academy import parse_academy_html
from app.gate import Store


FIXTURE = Path(__file__).parent / "fixtures" / "academy_indicators.html"


@pytest.fixture
def skills_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dest = tmp_path / "skills"
    dest.mkdir()
    monkeypatch.setenv("SKILLS_DIR", str(dest))
    return dest


@pytest.fixture
def store() -> Store:
    return Store()


@pytest.fixture
def academy_cite():
    return parse_academy_html(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def client(skills_dir: Path, academy_cite, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    main_mod._store = Store()
    main_mod.set_academy(academy_cite)
    monkeypatch.setattr(main_mod, "fetch_academy_indicators", lambda **_: academy_cite)
    monkeypatch.setattr(academy_mod, "fetch_academy_indicators", lambda **_: academy_cite)
    with TestClient(main_mod.app) as test_client:
        yield test_client
