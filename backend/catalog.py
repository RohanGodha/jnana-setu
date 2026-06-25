"""Book catalog + author aggregation + daily-reflection sampling.

Reads the master ``books.json`` (data layer) and provides the data behind the
/books, /authors and /daily-reflection endpoints.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from config import settings
from prompts import ANUYOGA_LABELS

# Author display names (08-FRONTEND-SPEC.md AUTHORS list)
AUTHOR_NAMES = {
    "canonical": "Canonical Texts",
    "vidyasagar": "Acharya Vidyasagar Ji Maharaj",
    "vidyananda": "Acharya Vidyananda Ji Maharaj",
    "tarun_sagar": "Muni Tarun Sagar Ji Maharaj",
    "gyanmati": "Aryika Gyanmati Mataji",
    "pushpadant_sagar": "Acharya Pushpadant Sagar Ji Maharaj",
    "deshbhushan": "Acharya Deshbhushan Ji Maharaj",
    "gupti_sagar": "Upadhyay Gupti Sagar Ji Maharaj",
    "vardhaman_sagar": "Acharya Vardhaman Sagar Ji Maharaj",
    "praman_sagar": "Muni Praman Sagar Ji Maharaj",
    "nirbhay_sagar": "Acharya Nirbhay Sagar Ji Maharaj",
    "pulak_sagar": "Pulak Sagar Ji Maharaj",
}


@lru_cache
def _load_books() -> list[dict]:
    path = Path(settings.books_json)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def reload_books() -> None:
    _load_books.cache_clear()


def list_books(
    page: int = 1,
    per_page: int = 24,
    anuyoga: Optional[str] = None,
    author_slug: Optional[str] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
) -> dict:
    books = _load_books()

    def keep(b: dict) -> bool:
        if anuyoga and anuyoga != "all_texts" and b.get("anuyoga") != anuyoga:
            return False
        if author_slug and author_slug != "all" and b.get("author_slug") != author_slug:
            return False
        if language and b.get("language") != language:
            return False
        if search:
            q = search.lower()
            hay = f"{b.get('title','')} {b.get('title_hindi','')} {b.get('author','')}".lower()
            if q not in hay:
                return False
        return True

    filtered = [b for b in books if keep(b)]
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    start = (page - 1) * per_page
    window = filtered[start : start + per_page]
    return {
        "total": len(filtered),
        "page": page,
        "per_page": per_page,
        "books": [_summary(b) for b in window],
    }


def get_book(book_id: str) -> Optional[dict]:
    for b in _load_books():
        if b.get("id") == book_id:
            detail = _summary(b)
            detail.update(
                {
                    "anuyoga_label": ANUYOGA_LABELS.get(b.get("anuyoga", ""), ""),
                    "description": b.get("description", ""),
                    "source_url": b.get("source_url", ""),
                }
            )
            return detail
    return None


def list_authors() -> list[dict]:
    books = _load_books()
    counts: dict[str, int] = {}
    anuyogas: dict[str, dict[str, int]] = {}
    for b in books:
        slug = b.get("author_slug", "canonical")
        counts[slug] = counts.get(slug, 0) + 1
        anuyogas.setdefault(slug, {})
        a = b.get("anuyoga", "all_texts")
        anuyogas[slug][a] = anuyogas[slug].get(a, 0) + 1

    out = []
    for slug, name in AUTHOR_NAMES.items():
        primary = "all_texts"
        if anuyogas.get(slug):
            primary = max(anuyogas[slug].items(), key=lambda kv: kv[1])[0]
        out.append(
            {
                "slug": slug,
                "name": name,
                "book_count": counts.get(slug, 0),
                "primary_anuyoga": primary,
                "era": "ancient" if slug == "canonical" else "contemporary",
            }
        )
    return out


def daily_reflection(use_llm: bool = True) -> dict:
    """Pull a deterministic-per-day passage and (optionally) an LLM contemplation."""
    books = [b for b in _load_books() if b.get("sample_passage")]
    now = datetime.now(timezone.utc)
    if not books:
        return {
            "text": "The pure soul, distinct from all karmic matter, is the true Self.",
            "text_translated": "",
            "reflection": "Contemplate the distinction between the knower and the known.",
            "source": {"title": "Samayasara", "author": "Acharya Kundakunda", "chapter": "Jiva Adhikar"},
            "generated_at": now,
        }
    seed = int(now.strftime("%Y%m%d"))
    book = random.Random(seed).choice(books)
    passage = book["sample_passage"]
    reflection = ""
    if use_llm:
        try:
            import llm
            import prompts

            reflection = llm.complete(
                prompts.DAILY_SYSTEM,
                prompts.DAILY_USER.format(
                    title=book["title"],
                    author=book["author"],
                    chapter=book.get("sample_chapter", "Unknown"),
                    passage_text=passage,
                ),
                temperature=0.4,
                max_tokens=400,
            )
        except Exception:
            reflection = ""
    return {
        "text": passage,
        "text_translated": book.get("sample_passage_translated", ""),
        "reflection": reflection,
        "source": {
            "title": book["title"],
            "author": book["author"],
            "chapter": book.get("sample_chapter", "Unknown"),
        },
        "generated_at": now,
    }


def _summary(b: dict) -> dict:
    return {
        "id": b.get("id", ""),
        "title": b.get("title", ""),
        "title_hindi": b.get("title_hindi", ""),
        "author": b.get("author", ""),
        "author_slug": b.get("author_slug", "canonical"),
        "anuyoga": b.get("anuyoga", "all_texts"),
        "language": b.get("language", "unknown"),
        "century": b.get("century", ""),
        "total_chunks": b.get("total_chunks", 0),
    }
