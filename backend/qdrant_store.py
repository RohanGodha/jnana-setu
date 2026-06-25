"""Hosted vector store backend (Qdrant Cloud).

Keeps the multi-GB index off the local disk and out of local RAM: vectors are
stored server-side (on-disk + scalar-quantized so they fit a free-tier cluster),
and search runs remotely. One collection holds every chunk; the Anuyoga and
author are payload fields used as query-time filters.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from config import settings


def _client():
    from qdrant_client import QdrantClient

    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=120,
        prefer_grpc=False,
    )


class QdrantStore:
    def __init__(self) -> None:
        self._c = None
        self.collection = settings.qdrant_collection

    @property
    def client(self):
        if self._c is None:
            self._c = _client()
        return self._c

    # --- schema -------------------------------------------------------------
    def ensure_collection(self, dim: int, recreate: bool = False) -> None:
        from qdrant_client import models as qm

        exists = self.client.collection_exists(self.collection)
        if exists and recreate:
            self.client.delete_collection(self.collection)
            exists = False
        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(
                    size=dim,
                    distance=qm.Distance.COSINE,
                    on_disk=True,  # keep vectors on disk -> low RAM
                ),
                quantization_config=qm.ScalarQuantization(
                    scalar=qm.ScalarQuantizationConfig(
                        type=qm.ScalarType.INT8, always_ram=False
                    )
                ),
                on_disk_payload=True,
            )
            # Payload indexes for fast filtering.
            for field in ("anuyoga", "author_slug"):
                try:
                    self.client.create_payload_index(
                        self.collection, field_name=field,
                        field_schema=qm.PayloadSchemaType.KEYWORD,
                    )
                except Exception:
                    pass

    # --- write --------------------------------------------------------------
    def upsert(self, ids, vectors, payloads) -> None:
        from qdrant_client import models as qm

        points = [
            qm.PointStruct(id=i, vector=v, payload=p)
            for i, v, p in zip(ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=self.collection, points=points, wait=False)

    # --- read ---------------------------------------------------------------
    def search(
        self, vector, top_k: int, anuyoga: str = "all_texts",
        author_filter: Optional[list[str]] = None,
    ) -> list[dict]:
        from qdrant_client import models as qm

        must = []
        if anuyoga and anuyoga != "all_texts":
            must.append(qm.FieldCondition(key="anuyoga", match=qm.MatchValue(value=anuyoga)))
        authors = [a for a in (author_filter or []) if a and a != "all"]
        if authors:
            must.append(qm.FieldCondition(key="author_slug", match=qm.MatchAny(any=authors)))
        flt = qm.Filter(must=must) if must else None

        res = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            query_filter=flt,
            with_payload=True,
            search_params=qm.SearchParams(quantization=qm.QuantizationSearchParams(rescore=True)),
        ).points
        out = []
        for p in res:
            payload = p.payload or {}
            out.append({"id": str(p.id), "document": payload.get("document", ""), **payload})
        return out

    def count(self) -> int:
        try:
            return self.client.count(self.collection, exact=False).count
        except Exception:
            return 0

    def health(self) -> str:
        try:
            self.client.get_collections()
            return "connected"
        except Exception:
            return "unavailable"


@lru_cache
def get_store() -> QdrantStore:
    return QdrantStore()
