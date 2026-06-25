"""Embedding backends for Jnana Setu.

Two backends:
- ``e5``   : production. intfloat/multilingual-e5-large via sentence-transformers.
             Requires the e5 prefix convention ("query: " / "passage: ").
- ``hash`` : zero-dependency deterministic dev fallback so the whole pipeline can
             run (and tests pass) without downloading a 560M-param model.

Both expose the same interface:
    embed_passages(list[str]) -> list[list[float]]
    embed_query(str)          -> list[float]
"""
from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from typing import Protocol

from config import settings

# multilingual-e5-large is 1024-dim; keep the fallback identical so a store built
# with one backend stays dimension-compatible if you swap (re-ingest recommended).
EMBED_DIM = 1024


class Embedder(Protocol):
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class HashEmbedder:
    """Deterministic bag-of-words hashing embedder.

    Not semantically strong, but stable and dependency-free. Good enough to make
    retrieval demonstrably work end-to-end in development/CI.
    """

    def __init__(self, dim: int = EMBED_DIM) -> None:
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = [t for t in _tokenize(text) if t]
        for tok in tokens:
            h = hashlib.md5(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if h[4] % 2 == 0 else -1.0
            vec[idx] += sign
        return _l2_normalize(vec)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class E5Embedder:
    """Production embedder using intfloat/multilingual-e5-large."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # heavy import

        self.model = SentenceTransformer(model_name)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {t}" for t in texts]
        vecs = self.model.encode(
            prefixed, normalize_embeddings=True, batch_size=32, show_progress_bar=False
        )
        return [v.tolist() for v in vecs]

    def embed_query(self, text: str) -> list[float]:
        vec = self.model.encode(
            [f"query: {text}"], normalize_embeddings=True, show_progress_bar=False
        )
        return vec[0].tolist()


def _tokenize(text: str) -> list[str]:
    import re

    # Keep Devanagari + Latin word characters; lowercase Latin.
    return re.findall(r"[\u0900-\u097F]+|[a-zA-Z0-9]+", text.lower())


@lru_cache
def get_embedder() -> Embedder:
    backend = settings.embedding_backend.lower()
    if backend == "e5":
        try:
            return E5Embedder(settings.embedding_model)
        except Exception as exc:  # pragma: no cover - depends on optional heavy deps
            print(f"[embeddings] e5 backend unavailable ({exc}); falling back to hash.")
            return HashEmbedder()
    return HashEmbedder()
