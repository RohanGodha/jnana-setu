"""Hybrid retrieval: dense (ChromaDB) + sparse (BM25), merged with Reciprocal
Rank Fusion, then an optional cross-encoder re-rank.

Collections mirror the four Anuyogas plus ``all_texts`` (02-ARCHITECTURE.md).
A BM25 corpus snapshot is persisted next to the Chroma store so the sparse index
can be rebuilt on startup without re-reading the source books.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from config import settings
from embeddings import get_embedder

ANUYOGA_COLLECTIONS = [
    "dravyanuyog",
    "charananuyog",
    "prathamanuyoga",
    "karnanuyoga",
    "all_texts",
]

_BM25_SNAPSHOT = "bm25_corpus.json"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\u0900-\u097F]+|[a-zA-Z0-9]+", text.lower())


def _snapshot_path() -> Path:
    return Path(settings.chroma_persist_path) / _BM25_SNAPSHOT


class Retriever:
    def __init__(self) -> None:
        self._client = None
        self._collections: dict = {}
        self._bm25 = None
        self._bm25_corpus: list[dict] = []
        self._embedder = get_embedder()

    # --- Chroma plumbing ----------------------------------------------------
    @property
    def client(self):
        if self._client is None:
            import chromadb

            os.makedirs(settings.chroma_persist_path, exist_ok=True)
            self._client = chromadb.PersistentClient(path=settings.chroma_persist_path)
        return self._client

    def collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"}
            )
        return self._collections[name]

    # --- BM25 (sparse) ------------------------------------------------------
    def _ensure_bm25(self) -> None:
        if self._bm25 is not None:
            return
        snap = _snapshot_path()
        if not snap.exists():
            self._bm25 = False  # mark "attempted, empty"
            self._bm25_corpus = []
            return
        from rank_bm25 import BM25Okapi

        with snap.open("r", encoding="utf-8") as fh:
            self._bm25_corpus = json.load(fh)
        tokenized = [_tokenize(d["document"]) for d in self._bm25_corpus]
        self._bm25 = BM25Okapi(tokenized) if tokenized else False

    def append_bm25_snapshot(self, records: list[dict]) -> None:
        """Persist documents for the BM25 sparse index during ingestion."""
        snap = _snapshot_path()
        snap.parent.mkdir(parents=True, exist_ok=True)
        existing: list[dict] = []
        if snap.exists():
            with snap.open("r", encoding="utf-8") as fh:
                existing = json.load(fh)
        existing.extend(records)
        with snap.open("w", encoding="utf-8") as fh:
            json.dump(existing, fh, ensure_ascii=False)
        # invalidate cache
        self._bm25 = None

    # --- Filters ------------------------------------------------------------
    @staticmethod
    def _build_where(author_filter: Optional[list[str]]) -> Optional[dict]:
        authors = [a for a in (author_filter or []) if a and a != "all"]
        if not authors:
            return None
        return {"author_slug": {"$in": authors}}

    @staticmethod
    def _matches_filters(meta: dict, anuyoga: str, authors: list[str]) -> bool:
        if anuyoga and anuyoga != "all_texts" and meta.get("anuyoga") != anuyoga:
            return False
        if authors and meta.get("author_slug") not in authors:
            return False
        return True

    # --- Dense search -------------------------------------------------------
    def _dense_search(
        self, query: str, anuyoga: str, author_filter: Optional[list[str]], top_k: int
    ) -> list[dict]:
        coll_name = anuyoga if anuyoga in ANUYOGA_COLLECTIONS else "all_texts"
        coll = self.collection(coll_name)
        if coll.count() == 0:
            coll = self.collection("all_texts")
        q_vec = self._embedder.embed_query(query)
        where = self._build_where(author_filter)
        try:
            res = coll.query(
                query_embeddings=[q_vec],
                n_results=min(top_k, max(coll.count(), 1)),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []
        out = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        for cid, doc, meta in zip(ids, docs, metas):
            out.append({"id": cid, "document": doc, **(meta or {})})
        return out

    # --- Sparse search ------------------------------------------------------
    def _sparse_search(
        self, query: str, anuyoga: str, author_filter: Optional[list[str]], top_k: int
    ) -> list[dict]:
        self._ensure_bm25()
        if not self._bm25:
            return []
        authors = [a for a in (author_filter or []) if a and a != "all"]
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
        out = []
        for i in ranked:
            if scores[i] <= 0:
                break
            rec = self._bm25_corpus[i]
            meta = rec.get("metadata", {})
            if not self._matches_filters(meta, anuyoga, authors):
                continue
            out.append({"id": rec["id"], "document": rec["document"], **meta})
            if len(out) >= top_k:
                break
        return out

    # --- Fusion -------------------------------------------------------------
    @staticmethod
    def _reciprocal_rank_fusion(
        dense: list[dict], sparse: list[dict], k: int
    ) -> list[dict]:
        scores: dict[str, float] = {}
        store: dict[str, dict] = {}
        for ranked in (dense, sparse):
            for rank, item in enumerate(ranked):
                cid = item["id"]
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
                store.setdefault(cid, item)
        ordered = sorted(scores.items(), key=lambda kv: -kv[1])
        return [store[cid] for cid, _ in ordered]

    # --- Re-rank ------------------------------------------------------------
    @lru_cache(maxsize=1)
    def _reranker(self):  # pragma: no cover - optional heavy dep
        from sentence_transformers import CrossEncoder

        return CrossEncoder(settings.rerank_model)

    def _rerank(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        if not settings.rerank_enabled or not chunks:
            return chunks[:top_k]
        try:  # pragma: no cover - optional
            pairs = [(query, c["document"]) for c in chunks]
            scores = self._reranker().predict(pairs)
            ranked = sorted(zip(chunks, scores), key=lambda x: -x[1])
            return [c for c, _ in ranked[:top_k]]
        except Exception:
            return chunks[:top_k]

    # --- Public API ---------------------------------------------------------
    def hybrid_search(
        self,
        query: str,
        anuyoga: str = "all_texts",
        author_filter: Optional[list[str]] = None,
    ) -> list[dict]:
        dense = self._dense_search(
            query, anuyoga, author_filter, settings.dense_top_k
        )
        sparse = self._sparse_search(
            query, anuyoga, author_filter, settings.sparse_top_k
        )

        # Author fallback: if filtering yielded too little, retry without it.
        if author_filter and (len(dense) + len(sparse)) < 3:
            dense = self._dense_search(query, anuyoga, None, settings.dense_top_k)
            sparse = self._sparse_search(query, anuyoga, None, settings.sparse_top_k)

        merged = self._reciprocal_rank_fusion(dense, sparse, settings.rrf_k)
        return self._rerank(query, merged[:20], settings.final_top_k)

    def health(self) -> str:
        try:
            self.client.heartbeat()
            return "connected"
        except Exception:
            return "unavailable"


class QdrantRetriever:
    """Hosted-backend retriever. Dense search runs server-side on Qdrant, so the
    index lives off local disk/RAM. Same public surface as ``Retriever``."""

    def __init__(self) -> None:
        from qdrant_store import get_store

        self._store = get_store()
        self._embedder = get_embedder()

    def _search(self, query, anuyoga, author_filter, top_k):
        vec = self._embedder.embed_query(query)
        return self._store.search(vec, top_k, anuyoga, author_filter)

    def hybrid_search(
        self,
        query: str,
        anuyoga: str = "all_texts",
        author_filter: Optional[list[str]] = None,
    ) -> list[dict]:
        k = max(settings.dense_top_k, settings.final_top_k)
        hits = self._search(query, anuyoga, author_filter, k)
        if author_filter and len(hits) < 3:  # author fallback
            hits = self._search(query, anuyoga, None, k)
        return hits[: settings.final_top_k]

    def health(self) -> str:
        return self._store.health()


@lru_cache
def get_retriever():
    if settings.vector_backend.lower() == "qdrant":
        return QdrantRetriever()
    return Retriever()
