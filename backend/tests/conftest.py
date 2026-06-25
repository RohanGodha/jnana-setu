"""Ensure the seed corpus is ingested before the API tests run.

Keeps the suite self-contained: on a fresh checkout / CI runner where the
ChromaDB store is empty, this builds it from the seeded passages in books.json.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def pytest_configure(config):  # noqa: ARG001
    from retriever import get_retriever

    retriever = get_retriever()
    try:
        count = retriever.collection("all_texts").count()
    except Exception:
        count = 0
    if count == 0:
        import ingest

        ingest.run(reset=True)
