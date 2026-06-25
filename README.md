# Jnana Setu (ज्ञान सेतु) — "Bridge of Knowledge"

A RAG chatbot over Digambar Jain literature: **50 canonical texts + 11 contemporary
Acharyas × 50 works = 600 books**. Every answer is grounded in retrieved passages
and cited to its source.

> **Stack:** FastAPI · LangGraph · ChromaDB (embedded) · BM25 hybrid retrieval ·
> Claude Sonnet/Haiku · React + Vite + TypeScript + Tailwind + Zustand

This repository contains the full, runnable implementation of the design described
in `00-PROJECT-INDEX.md` … `10-MONETIZATION.md`.

---

## What's built

| Layer | Status |
|-------|--------|
| Ingestion pipeline (parse → clean → chapter-aware chunk → embed → ChromaDB + BM25) | ✅ `backend/ingest.py` |
| Hybrid retrieval (dense + BM25 + Reciprocal Rank Fusion + optional cross-encoder rerank) | ✅ `backend/retriever.py` |
| LangGraph pipeline (router → retrieval → generator → hallucination guard) | ✅ `backend/graph.py` |
| **Guru mode** — empathetic life guidance grounded in Jain psychology | ✅ `backend/concepts.py` + guidance prompts |
| FastAPI backend (auth, JWT, rate limits, SSE streaming, books, authors, daily reflection) | ✅ `backend/main.py` |
| React frontend (Home, Chat w/ SSE, Library explorer, Login) | ✅ `frontend/` |
| Seed corpus (600-book catalog + passages for well-known canonical texts) | ✅ `data/books.json` |
| Docker / docker-compose / nginx | ✅ |
| Backend test suite | ✅ `backend/tests/` (9 tests) |

### Two ways to talk to it
- **Scholarly mode** — ask a doctrinal/historical question, get a precise, cited answer.
- **Guru mode** — *share a real struggle* ("my partner betrayed me and I'm furious").
  The router detects a personal life problem, maps the felt experience to Jain psychology
  (kasaya/passions, raga-dvesha/attachment, anekanta/perspective, anitya/impermanence,
  the witnessing self), expands retrieval by those concepts, and replies as a warm
  mentor: **sees the feeling first → illuminates gently through cited teachings → offers
  one small practice.** Answers default to **~80–100 words and scale with how much the
  person shares.** Acute-distress language triggers a **caring safety response** with
  helpline guidance instead of scripture-as-cure. See `backend/concepts.py`,
  `prompts.GUIDANCE_SYSTEM`, and `graph._length_directive`.

### Runs offline out of the box
With **no `ANTHROPIC_API_KEY`**, the backend runs in **mock mode**: the router/guard
use heuristics and the generator assembles a grounded, cited answer from the retrieved
passages. With **no `EMBEDDING_BACKEND=e5`**, a deterministic hash embedder is used so
retrieval works without downloading a 560M-param model. Flip both on for production.

---

## Quick start (local, no API key needed)

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows  (source venv/bin/activate on *nix)
pip install -r requirements.txt
copy .env.example .env          # cp on *nix

python ingest.py --reset        # builds ChromaDB + BM25 from the seeded passages
uvicorn main:app --reload --port 8000
```

Health check: <http://localhost:8000/health> → `{"status":"ok", ...}`

### 2. Frontend

```bash
cd frontend
npm install
copy .env.example .env.local    # VITE_API_URL=/api (proxied to :8000 by Vite)
npm run dev                     # http://localhost:5173
```

Open <http://localhost:5173>, create an account, and ask:
*"What does Samayasara say about the nature of the soul?"*

---

## Going to production

1. **Embeddings:** set `EMBEDDING_BACKEND=e5` (downloads `intfloat/multilingual-e5-large`).
   Optionally `RERANK_ENABLED=true` for the `mxbai-rerank-large-v1` cross-encoder.
2. **LLM:** set `ANTHROPIC_API_KEY` (and `GENERATOR_MODEL` / `GUARD_MODEL` if needed).
3. **Corpus:** drop real PDFs/TXT/HTML into `data/…`, point each `books.json` entry's
   `file_path` at the file, then re-run `python ingest.py --reset`.
4. **Secrets:** generate `JWT_SECRET` (`openssl rand -hex 32`) and set `CORS_ORIGINS`.

### Docker

```bash
docker compose up --build
# frontend  → http://localhost:3000
# backend   → http://localhost:8000
# Run ingestion once inside the backend container:
docker compose exec backend python ingest.py --reset
```

---

## Architecture (request lifecycle)

```
React (SSE)  ─POST /query─►  FastAPI  ─►  LangGraph
                                            ├─ query_router        (classify → anuyoga/author/lang)
                                            ├─ retrieval_agent      (ChromaDB dense + BM25 sparse → RRF → rerank)
                                            ├─ generator            (Claude Sonnet, streamed)
                                            └─ hallucination_guard  (Claude Haiku verifies citations)
                                                  │
   ChatWindow ◄── token / citations / done SSE ───┘
```

See `02-ARCHITECTURE.md` and `03-WORKFLOW.md` for full diagrams.

---

## API summary

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/auth/register` | – | create account |
| POST | `/auth/login` | – | returns JWT |
| GET  | `/auth/me` | ✅ | tier + daily usage |
| POST | `/query` | ✅ | **SSE** stream; free tier 3/day, Hindi = premium |
| GET  | `/books` | – | paginated catalog (filter: anuyoga, author, language, search) |
| GET  | `/books/{id}` | – | single book |
| GET  | `/authors` | – | 12 author groups w/ counts |
| POST | `/daily-reflection` | – | sutra of the day |
| GET  | `/health` | – | liveness |

Full contracts in `06-API-SPEC.md`.

---

## Tests

```bash
cd backend
venv\Scripts\python -m pytest -q     # 9 passing: auth, books, SSE query, rate limit, Hindi gate
```

---

## Repo layout

```
backend/      FastAPI app, LangGraph pipeline, retrieval, ingestion, auth, tests
frontend/     React + Vite SPA (pages, components, hooks, store, api)
data/         books.json (600 entries) + build_catalog.py generator
docker-compose.yml
00-…10-*.md   Design documents
```

---

## Notes & honesty about the corpus

- The 50 canonical texts have full metadata; ~10 well-known ones ship with concise,
  **representative English renderings** as seed passages so retrieval is demonstrable.
  These are placeholders — replace with parsed source text for production use.
- The 550 Acharya entries provide catalog metadata; titles for the five well-documented
  authors come from `04-BOOK-CORPUS.md`, the rest are numbered placeholders pending
  Phase-1 corpus collection.
- Always verify scriptural quotations against authoritative published editions before
  relying on them.
