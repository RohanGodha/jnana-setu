"""Extra read-only features: corpus stats, passage search (no LLM),
random sutra, per-book passages, related books, suggestions."""
from __future__ import annotations

import hashlib
import random
from collections import Counter

import catalog
from embeddings import get_embedder
from prompts import ANUYOGA_LABELS
from retriever import get_retriever

SUGGESTED_QUESTIONS = [
    "What does Samayasara say about the nature of the soul?",
    "Explain the Jain theory of karma and its eight types.",
    "What are the five great vows (mahavratas)?",
    "Describe the structure of Jambudvipa in Jain cosmology.",
    "What is anekantavada and the doctrine of syadvada?",
    "How should a householder (shravaka) practice non-violence?",
    "What is the path to liberation (moksha) in Jainism?",
    "Who was Lord Mahavira and what did he teach?",
    "What are the twelve reflections (anuprekshas)?",
    "Explain the difference between nishchaya and vyavahara naya.",
]


def corpus_stats() -> dict:
    books = catalog._load_books()
    with_files = [b for b in books if b.get("file_path")]
    by_anuyoga = Counter(b.get("anuyoga", "all_texts") for b in with_files)
    by_author = Counter(b.get("author_slug", "canonical") for b in with_files)
    by_language = Counter((b.get("language") or "unknown") for b in with_files)
    total_chunks = sum(int(b.get("total_chunks", 0) or 0) for b in books)
    by_source = Counter(
        ("archive.org" if b.get("id", "").startswith(("canonical", "harvest"))
         else "wikisource" if b.get("id", "").startswith("wiki")
         else "github" if b.get("id", "").startswith("gh")
         else "catalog")
        for b in with_files
    )
    return {
        "total_books": len(with_files),
        "catalog_entries": len(books),
        "total_chunks": total_chunks,
        "anuyogas": dict(by_anuyoga),
        "languages": dict(by_language.most_common(12)),
        "sources": dict(by_source),
        "top_authors": [
            {"author_slug": s, "count": c} for s, c in by_author.most_common(12)
        ],
    }


def passage_search(query: str, anuyoga: str = "all_texts",
                   author_filter=None, limit: int = 8) -> list[dict]:
    """Semantic passage search without LLM generation."""
    r = get_retriever()
    hits = r.hybrid_search(query, anuyoga or "all_texts", author_filter or [])
    out = []
    for h in hits[:limit]:
        out.append({
            "book_id": h.get("book_id", h.get("id", "")),
            "title": h.get("title", "Unknown"),
            "author": h.get("author", "Unknown"),
            "anuyoga": h.get("anuyoga", "all_texts"),
            "chapter": h.get("chapter", "Unknown"),
            "excerpt": (h.get("document", "") or "")[:400].strip(),
        })
    return out


def random_sutra() -> dict:
    """Return a pseudo-random passage from the corpus via a random query vector."""
    seed = random.randint(0, 1_000_000)
    token = hashlib.md5(str(seed).encode()).hexdigest()
    try:
        from qdrant_store import get_store
        store = get_store()
        vec = get_embedder().embed_query(token)
        hits = store.search(vec, top_k=5)
        if hits:
            h = random.choice(hits)
            return {
                "book_id": h.get("book_id", ""),
                "title": h.get("title", "Unknown"),
                "author": h.get("author", "Unknown"),
                "anuyoga": h.get("anuyoga", "all_texts"),
                "excerpt": (h.get("document", "") or "")[:500].strip(),
            }
    except Exception:
        pass
    return {"book_id": "", "title": "Samayasara", "author": "Acharya Kundakunda",
            "anuyoga": "dravyanuyog",
            "excerpt": "The soul is, by nature, pure consciousness, forever distinct from karmic matter."}


def book_passages(book_id: str, limit: int = 6) -> list[dict]:
    try:
        from qdrant_store import get_store
        store = get_store()
        from qdrant_client import models as qm
        res, _ = store.client.scroll(
            collection_name=store.collection,
            scroll_filter=qm.Filter(must=[
                qm.FieldCondition(key="book_id", match=qm.MatchValue(value=book_id))
            ]),
            limit=limit, with_payload=True,
        )
        return [
            {"chapter": p.payload.get("chapter", "Unknown"),
             "excerpt": (p.payload.get("document", "") or "")[:500].strip()}
            for p in res
        ]
    except Exception:
        return []


def related_books(book_id: str, limit: int = 6) -> list[dict]:
    books = catalog._load_books()
    target = next((b for b in books if b.get("id") == book_id), None)
    if not target:
        return []
    same_author = [b for b in books if b.get("author_slug") == target.get("author_slug")
                   and b.get("id") != book_id and b.get("file_path")]
    same_anuyoga = [b for b in books if b.get("anuyoga") == target.get("anuyoga")
                    and b.get("id") != book_id and b.get("file_path")]
    seen, out = set(), []
    for b in (same_author + same_anuyoga):
        if b["id"] in seen:
            continue
        seen.add(b["id"])
        out.append(catalog._summary(b))
        if len(out) >= limit:
            break
    return out


def suggestions(prefix: str = "") -> list[str]:
    import db
    pop = [p["query"] for p in db.popular_queries(8)]
    base = pop + [q for q in SUGGESTED_QUESTIONS if q not in pop]
    if prefix:
        p = prefix.lower()
        base = [q for q in base if p in q.lower()] or base
    return base[:10]
