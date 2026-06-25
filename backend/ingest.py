"""Offline ingestion pipeline (03-WORKFLOW.md, Workflow 1).

For every book in ``books.json``:
    parse -> clean -> chapter-aware chunk -> embed -> upsert to ChromaDB
Then persist the BM25 corpus snapshot for sparse retrieval.

Parsers: PDF (PyMuPDF), TXT (plain), HTML (BeautifulSoup). If a book has no
``file_path`` on disk but provides a ``sample_passage`` (seed data), that passage
is ingested so the system is queryable out of the box.

Usage:
    python ingest.py                # ingest everything in books.json
    python ingest.py --reset        # wipe collections first
    python ingest.py --limit 5      # ingest only first 5 books (smoke test)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

try:  # Unicode-safe console output on Windows (cp1252) for non-Latin titles.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import settings
from embeddings import get_embedder
from retriever import ANUYOGA_COLLECTIONS, get_retriever

CHUNK_SIZE = settings.ingest_chunk_size       # coarser for hosted DB (set in .env)
CHUNK_OVERLAP = settings.ingest_chunk_overlap
CHAPTER_PATTERN = re.compile(r"(Chapter\s+\d+|अध्याय\s*\d*|Adhyay\s*\d*|।।\s*\d+\s*।।)")


# --- Parsing ----------------------------------------------------------------
def parse_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import fitz  # PyMuPDF

        doc = fitz.open(str(path))
        return "\n".join(page.get_text() for page in doc)
    if suffix in {".html", ".htm"}:
        from bs4 import BeautifulSoup

        return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser").get_text()
    # .txt and everything else: plain read
    return path.read_text(encoding="utf-8", errors="ignore")


# --- Cleaning ---------------------------------------------------------------
def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Drop bare page numbers / very short boilerplate lines.
        if re.fullmatch(r"\d{1,4}", stripped):
            continue
        lines.append(stripped)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# --- Chapter-aware chunking -------------------------------------------------
def split_chapters(text: str) -> list[tuple[str, str]]:
    """Return (chapter_label, chapter_text) segments."""
    matches = list(CHAPTER_PATTERN.finditer(text))
    if not matches:
        return [("Unknown", text)]
    segments = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segments.append((m.group(0).strip(), text[start:end].strip()))
    # Preamble before the first chapter heading.
    if matches[0].start() > 0:
        segments.insert(0, ("Preamble", text[: matches[0].start()].strip()))
    return [s for s in segments if s[1]]


def chunk_text(text: str) -> list[str]:
    """Recursive character splitter (≈512 tokens, 64 overlap)."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE * 4,  # ~4 chars/token heuristic
            chunk_overlap=CHUNK_OVERLAP * 4,
            separators=["\n\n", "\n", "।", ". ", " "],
        )
        return [c for c in splitter.split_text(text) if c.strip()]
    except Exception:
        return _naive_chunk(text)


def _naive_chunk(text: str) -> list[str]:
    size, overlap = CHUNK_SIZE * 4, CHUNK_OVERLAP * 4
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return [c.strip() for c in chunks if c.strip()]


# --- Book -> chunk records --------------------------------------------------
def book_to_chunks(book: dict, base_dir: Path) -> list[dict]:
    raw = ""
    file_path = book.get("file_path")
    if file_path:
        # file_path may be absolute, relative to project root (e.g.
        # "backend/books/x.txt"), or relative to the data/ dir. Try each.
        candidates = [
            Path(file_path),
            base_dir.parent / file_path,   # project root (data/..)
            base_dir / file_path,          # data/ dir
        ]
        path = next((p for p in candidates if p.exists()), None)
        if path:
            raw = parse_file(path)
    if not raw and book.get("sample_passage"):
        raw = book["sample_passage"]
    if not raw:
        return []

    cleaned = clean_text(raw)
    records: list[dict] = []
    idx = 0
    for chapter_label, chapter_text in split_chapters(cleaned):
        for chunk in chunk_text(chapter_text):
            records.append(
                {
                    "id": f"{book['id']}_{idx}",
                    "document": chunk,
                    "metadata": {
                        "book_id": book["id"],
                        "title": book.get("title", ""),
                        "title_hindi": book.get("title_hindi", ""),
                        "author": book.get("author", ""),
                        "author_slug": book.get("author_slug", "canonical"),
                        "anuyoga": book.get("anuyoga", "all_texts"),
                        "language": book.get("language", "unknown"),
                        "chapter": book.get("sample_chapter") or chapter_label,
                        "chunk_index": idx,
                        "source_type": book.get("source_type", "text"),
                    },
                }
            )
            idx += 1
    return records


# --- Qdrant (hosted) ingest -------------------------------------------------
def run_qdrant(reset: bool = False, limit: int | None = None) -> None:
    """Stream chunks into a hosted Qdrant collection. Bounded memory (no BM25
    accumulation), vectors stored server-side. UUID point ids derived from the
    deterministic chunk id; the original id is kept in the payload."""
    import uuid

    from qdrant_store import get_store

    base_dir = Path(settings.books_json).resolve().parent
    books_path = Path(settings.books_json)
    if not books_path.exists():
        sys.exit(f"books.json not found at {books_path}")

    with books_path.open("r", encoding="utf-8") as fh:
        all_books = json.load(fh)
    books = all_books[:limit] if limit else all_books

    embedder = get_embedder()
    store = get_store()
    dim = len(embedder.embed_query("dimension probe"))
    store.ensure_collection(dim, recreate=reset)

    log_dir = base_dir.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"ingest_qdrant_{datetime.now():%Y%m%d_%H%M%S}.log"
    total_chunks = 0
    BATCH = 256

    with log_path.open("w", encoding="utf-8") as log:
        for i, book in enumerate(books, 1):
            records = book_to_chunks(book, base_dir)
            if not records:
                line = f"[SKIP] {book['id']} {book.get('title','')} (no text)"
                print(line); log.write(line + "\n")
                continue
            n = 0
            for s in range(0, len(records), BATCH):
                batch = records[s : s + BATCH]
                docs = [r["document"] for r in batch]
                vecs = embedder.embed_passages(docs)
                ids, payloads = [], []
                for r in batch:
                    ids.append(str(uuid.uuid5(uuid.NAMESPACE_URL, r["id"])))
                    payloads.append({"chunk_id": r["id"], "document": r["document"], **r["metadata"]})
                try:
                    store.upsert(ids, vecs, payloads)
                except Exception as exc:
                    print(f"    ! upsert failed for {book['id']} batch {s}: {exc}")
                    log.write(f"upsert fail {book['id']} {s}: {exc}\n")
                    continue
                n += len(batch)
            total_chunks += n
            book["total_chunks"] = n
            line = f"[{i}/{len(books)}] {book['id']} {book.get('title','')}: {n} chunks"
            print(line); log.write(line + "\n")

        summary = f"DONE (qdrant). {total_chunks} chunks across {len(books)} books -> {log_path}"
        print(summary); log.write(summary + "\n")

    with books_path.open("w", encoding="utf-8") as fh:
        json.dump(all_books, fh, ensure_ascii=False, indent=2)


# --- Main -------------------------------------------------------------------
def run(reset: bool = False, limit: int | None = None) -> None:
    if settings.vector_backend.lower() == "qdrant":
        return run_qdrant(reset=reset, limit=limit)

    base_dir = Path(settings.books_json).resolve().parent
    books_path = Path(settings.books_json)
    if not books_path.exists():
        sys.exit(f"books.json not found at {books_path}")

    with books_path.open("r", encoding="utf-8") as fh:
        all_books = json.load(fh)
    # NB: ``books`` is a view to process; ``all_books`` is always what we persist
    # so a ``--limit`` smoke test can never truncate the full catalog on disk.
    books = all_books[:limit] if limit else all_books

    retriever = get_retriever()
    embedder = get_embedder()

    if reset:
        for name in ANUYOGA_COLLECTIONS:
            try:
                retriever.client.delete_collection(name)
            except Exception:
                pass
        snap = Path(settings.chroma_persist_path) / "bm25_corpus.json"
        snap.unlink(missing_ok=True)
        retriever._collections.clear()

    log_dir = base_dir.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"ingest_{datetime.now():%Y%m%d_%H%M%S}.log"
    total_chunks = 0
    bm25_records: list[dict] = []

    with log_path.open("w", encoding="utf-8") as log:
        for i, book in enumerate(books, 1):
            records = book_to_chunks(book, base_dir)
            if not records:
                line = f"[SKIP] {book['id']} {book.get('title','')} (no text)"
                print(line)
                log.write(line + "\n")
                continue

            docs = [r["document"] for r in records]
            metas = [r["metadata"] for r in records]
            ids = [r["id"] for r in records]
            embeddings = embedder.embed_passages(docs)

            anuyoga = book.get("anuyoga", "all_texts")
            target_collections = {"all_texts"}
            if anuyoga in ANUYOGA_COLLECTIONS:
                target_collections.add(anuyoga)
            # Chunk ids are unique within a collection, so the same id is reused
            # across collections. This lets RRF dedupe dense (per-anuyoga) and
            # sparse (global BM25) hits that refer to the same chunk.
            # ChromaDB caps a single upsert (~5461 records); batch large books.
            UPSERT_BATCH = 4000
            for coll_name in target_collections:
                coll = retriever.collection(coll_name)
                for s in range(0, len(ids), UPSERT_BATCH):
                    e = s + UPSERT_BATCH
                    coll.upsert(
                        ids=ids[s:e],
                        documents=docs[s:e],
                        embeddings=embeddings[s:e],
                        metadatas=metas[s:e],
                    )

            bm25_records.extend(records)
            total_chunks += len(records)
            book["total_chunks"] = len(records)
            line = f"[{i}/{len(books)}] {book['id']} {book.get('title','')}: {len(records)} chunks"
            print(line)
            log.write(line + "\n")

        retriever.append_bm25_snapshot(bm25_records)
        summary = f"DONE. {total_chunks} chunks across {len(books)} books -> {log_path}"
        print(summary)
        log.write(summary + "\n")

    # Persist updated total_chunks back to books.json. Always write the FULL
    # catalog (book dicts are shared references, so total_chunks updates on the
    # processed subset propagate) — never the limited subset.
    with books_path.open("w", encoding="utf-8") as fh:
        json.dump(all_books, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jnana Setu ingestion")
    parser.add_argument("--reset", action="store_true", help="wipe collections first")
    parser.add_argument("--limit", type=int, default=None, help="ingest only N books")
    args = parser.parse_args()
    run(reset=args.reset, limit=args.limit)
