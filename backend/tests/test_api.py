"""End-to-end API tests (run against mock mode + seeded ChromaDB).

Run: pytest -q   (from the backend/ directory, after `python ingest.py`)
"""
from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

client = TestClient(main.app)


def _register_and_login() -> str:
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/auth/register",
        json={"name": "Test Seeker", "email": email, "password": "password123"},
    )
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"


def test_books_pagination_and_filter():
    r = client.get("/books", params={"per_page": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 600
    assert len(body["books"]) == 10

    r = client.get("/books", params={"anuyoga": "dravyanuyog"})
    assert all(b["anuyoga"] == "dravyanuyog" for b in r.json()["books"])

    r = client.get("/books", params={"search": "Samayasara"})
    assert any("Samayasara" in b["title"] for b in r.json()["books"])


def test_book_detail_and_404():
    r = client.get("/books/canonical-012")
    assert r.status_code == 200
    assert r.json()["title"] == "Samayasara"
    assert client.get("/books/does-not-exist").status_code == 404


def test_authors():
    r = client.get("/authors")
    assert r.status_code == 200
    authors = r.json()
    assert len(authors) == 12
    assert any(a["slug"] == "vidyasagar" and a["book_count"] == 50 for a in authors)


def test_daily_reflection():
    r = client.post("/daily-reflection")
    assert r.status_code == 200
    assert r.json()["source"]["title"]


def test_auth_required_for_query():
    r = client.post("/query", json={"query": "What is the soul?"})
    assert r.status_code == 401


def test_query_sse_stream_and_citations():
    token = _register_and_login()
    r = client.post(
        "/query",
        json={"query": "What does Samayasara say about the nature of the soul?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    text = r.text
    assert "event: token" in text
    assert "event: citations" in text
    assert "event: done" in text
    assert "Samayasara" in text


def test_free_tier_rate_limit():
    token = _register_and_login()
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(3):
        assert client.post("/query", json={"query": "soul"}, headers=headers).status_code == 200
    # 4th query exceeds the free-tier daily limit of 3.
    r = client.post("/query", json={"query": "soul"}, headers=headers)
    assert r.status_code == 429


def test_hindi_blocked_for_free_tier():
    token = _register_and_login()
    r = client.post(
        "/query",
        json={"query": "आत्मा क्या है?", "language": "hi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def _stream(token: str, query: str) -> tuple[str, str]:
    """Return (raw_sse, reconstructed_answer_text) for a query."""
    import json

    r = client.post(
        "/query",
        json={"query": query},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    answer = ""
    for block in r.text.split("\n\n"):
        if "event: token" in block:
            for line in block.splitlines():
                if line.startswith("data:"):
                    try:
                        answer += json.loads(line[5:].strip())
                    except Exception:
                        pass
    return r.text, answer


def test_guidance_is_empathetic_and_cited():
    """A personal life problem should get an empathetic, guru-style, cited reply."""
    token = _register_and_login()
    raw, answer = _stream(
        token,
        "My business partner betrayed me and I am so angry I can't sleep. "
        "I feel like I want revenge.",
    )
    assert "event: citations" in raw
    assert "I hear you" in answer  # empathy first
    assert "[" in answer and "]" in answer  # grounded citation present


def test_scholarly_still_works():
    token = _register_and_login()
    _, answer = _stream(token, "What are the six substances (dravya)?")
    assert "tradition offers a clear teaching" in answer
    assert "I hear you" not in answer


def test_crisis_triggers_safety_response():
    token = _register_and_login()
    raw, answer = _stream(token, "I don't want to live anymore, I want to die.")
    assert "reach out" in answer.lower()  # urges human/professional help
    assert "9152987821" in answer  # helpline included
    assert "event: citations\ndata: []" in raw  # no fabricated citations
