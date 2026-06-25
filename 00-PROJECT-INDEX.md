# Jain RAG Chatbot — Project Index

> **Project name:** Jnana Setu (ज्ञान सेतु) — "Bridge of Knowledge"
> **Owner:** Rohan (Full Stack AI Engineer)
> **Stack:** FastAPI · LangGraph · ChromaDB · React · Claude Sonnet 4.6
> **Corpus:** 600 books — 50 canonical Digambar Jain texts + 11 Acharyas × 50 books each

---

## Document map

| File | Purpose |
|------|---------|
| `00-PROJECT-INDEX.md` | This file — start here |
| `01-TODOS.md` | Phase-wise task checklist |
| `02-ARCHITECTURE.md` | Full system architecture with component breakdown |
| `03-WORKFLOW.md` | Data flow diagrams and request lifecycle |
| `04-BOOK-CORPUS.md` | All 600 books listed by canonical + 11 Acharyas |
| `05-TECH-STACK.md` | Every library, version, and why it was chosen |
| `06-API-SPEC.md` | FastAPI endpoint contracts (request/response shapes) |
| `07-PROMPTS.md` | All LLM system prompts and RAG prompt templates |
| `08-FRONTEND-SPEC.md` | React component tree, pages, and UI states |
| `09-DEPLOYMENT.md` | Docker, Railway/Render deploy guide, env vars |
| `10-MONETIZATION.md` | Freemium tiers, feature gates, revenue roadmap |

---

## Quick start (once code is built)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python ingest.py          # Run once to build vector store
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Project status

- [~] Phase 1 — Corpus collection & metadata tagging — *catalog of 600 built (`data/books.json`); seed passages for canonical texts; real file collection pending*
- [x] Phase 2 — Ingestion pipeline — `backend/ingest.py`
- [x] Phase 3 — Vector store setup — embedded ChromaDB + BM25 hybrid (`backend/retriever.py`)
- [x] Phase 4 — LangGraph RAG orchestration — `backend/graph.py`
- [x] Phase 5 — FastAPI backend — `backend/main.py` (9 tests passing)
- [x] Phase 6 — React frontend — `frontend/`
- [x] Phase 7 — Deployment — Dockerfiles, docker-compose, nginx

> Code is implemented and runs end-to-end offline (mock LLM + hash embeddings).
> See `README.md` for run instructions and the production switches.

---

*Last updated: June 2026*
