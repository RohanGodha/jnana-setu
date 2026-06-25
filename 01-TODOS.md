# Todos — Jnana Setu RAG Chatbot

> Check off as you go. Each phase must be complete before moving to the next.

---

## Phase 1 — Corpus collection & metadata tagging

### Canonical 50 texts
- [ ] Download PDFs from jainebooks.org and JLOR GitHub
- [ ] Download from HathiTrust / Internet Archive for older texts
- [ ] Create `books.json` master catalog with fields:
  - `id`, `title`, `title_hindi`, `author`, `anuyoga`, `language`, `source_url`, `file_path`, `century`
- [ ] Tag each book with `anuyoga` category (Dravyanuyog / Charananuyog / Prathamanuyoga / Karnanuyoga)

### Modern Acharya books (11 × 50 = 550)
- [ ] Acharya Vidyasagar Ji — collect 50 books/texts (Muktadhara + other poetry + discourses)
- [ ] Acharya Vidyananda Ji — collect 50 (logic commentaries + pravachans)
- [ ] Muni Tarun Sagar Ji — collect 50 (Kadve Pravachan series + other books)
- [ ] Aryika Gyanmati Mataji — collect 50 (Jambudveepa texts + cosmology)
- [ ] Acharya Pushpadant Sagar Ji — collect 50 (karma discourses)
- [ ] Acharya Deshbhushan Ji — collect 50 (conduct texts)
- [ ] Upadhyay Gupti Sagar Ji — collect 50 (meditation / samayik)
- [ ] Acharya Vardhaman Sagar Ji — collect 50 (hagiographies)
- [ ] Muni Praman Sagar Ji — collect 50 (logic / tarkik discourses)
- [ ] Acharya Nirbhay Sagar Ji — collect 50 (charitra texts)
- [ ] Pulak Sagar Ji — collect 50 (modern ethical discourses)

### For audio-only Acharyas (Tarun Sagar, Pulak Sagar)
- [ ] Set up Whisper transcription pipeline
  ```bash
  pip install openai-whisper
  whisper audio.mp3 --language Hindi --output_format txt
  ```
- [ ] Manual review of transcripts for accuracy
- [ ] Save as `.txt` in `/data/transcripts/`

---

## Phase 2 — Ingestion pipeline

- [ ] Create `/backend/ingest.py` script
- [ ] Implement PDF parser using PyMuPDF
  ```python
  import fitz  # PyMuPDF
  doc = fitz.open("book.pdf")
  ```
- [ ] Implement `.txt` / `.html` parser fallback
- [ ] Build text cleaner (strip headers/footers, fix diacritics)
- [ ] Implement chapter-aware chunker
  - Chunk size: 512 tokens
  - Overlap: 64 tokens
  - Hard split at chapter/section headings
- [ ] Set up embedding model (`intfloat/multilingual-e5-large`)
- [ ] Test embedding on 5 sample books before full run
- [ ] Run full ingestion (expect 4–8 hours for 600 books)
- [ ] Verify chunk count and metadata completeness
- [ ] Save ingestion log to `/logs/ingest_YYYYMMDD.log`

---

## Phase 3 — Vector store

- [ ] Install ChromaDB: `pip install chromadb`
- [ ] Create 4 collections (one per Anuyoga):
  - `dravyanuyog`
  - `charananuyog`
  - `prathamanuyoga`
  - `karnanuyoga`
- [ ] Create `all_texts` collection (for cross-Anuyoga search)
- [ ] Add BM25 sparse index alongside dense vectors (via `rank_bm25`)
- [ ] Write `retriever.py` with hybrid search function
- [ ] Test retrieval with 10 sample queries
- [ ] Tune top-k (start at 8, adjust based on quality)
- [ ] Set up cross-encoder re-ranker (`mxbai-rerank-large-v1`)

---

## Phase 4 — LangGraph RAG orchestration

- [ ] Install: `pip install langgraph langchain-anthropic`
- [ ] Build `graph.py` with 4 nodes:
  - [ ] `query_router` — classifies query → sets anuyoga filter + author filter
  - [ ] `retrieval_agent` — fetches top-8, re-ranks
  - [ ] `generator` — calls Claude Sonnet 4.6 with context + citation mandate
  - [ ] `hallucination_guard` — verifies all citations exist in retrieved chunks
- [ ] Define state schema (`TypedDict`)
- [ ] Add conditional edges (router → correct collection)
- [ ] Test end-to-end with 20 diverse queries
- [ ] Add retry logic for failed retrievals
- [ ] Log all graph runs to LangSmith

---

## Phase 5 — FastAPI backend

- [ ] Scaffold project: `fastapi`, `uvicorn`, `pydantic`, `python-jose`
- [ ] Implement endpoints:
  - [ ] `POST /query` — main RAG query with SSE streaming
  - [ ] `GET /books` — paginated catalog
  - [ ] `GET /books/{id}` — single book detail
  - [ ] `POST /daily-reflection` — random sutra pull
  - [ ] `POST /auth/register` — user registration
  - [ ] `POST /auth/login` — JWT login
  - [ ] `GET /auth/me` — current user + tier
- [ ] Add JWT auth middleware
- [ ] Add rate limiting (free tier: 3 queries/day)
- [ ] Add CORS for React frontend
- [ ] Write Pydantic models for all request/response
- [ ] Add `/health` endpoint
- [ ] Write unit tests for all endpoints

---

## Phase 6 — React frontend

- [ ] Scaffold: `npm create vite@latest frontend -- --template react-ts`
- [ ] Install: `tailwindcss`, `axios`, `react-router-dom`, `zustand`
- [ ] Build pages:
  - [ ] `/` — Home with daily reflection + quick query
  - [ ] `/chat` — Main chat interface
  - [ ] `/books` — Book explorer (filter by Anuyoga + Author)
  - [ ] `/login` — Auth page
- [ ] Build components:
  - [ ] `ChatWindow` — SSE streaming message display
  - [ ] `CitationCard` — shows book title, author, chapter for each source
  - [ ] `AuthorFilterPanel` — multi-select for 11 Acharyas + canonical
  - [ ] `AnuyogaBadge` — color-coded category badge
  - [ ] `DailyReflection` — home screen sutra card
  - [ ] `BookExplorer` — searchable, filterable book grid
- [ ] Implement SSE streaming reader
- [ ] Add loading skeletons
- [ ] Mobile responsive layout
- [ ] Dark mode support

---

## Phase 7 — Deployment

- [ ] Write `Dockerfile` for FastAPI backend
- [ ] Write `docker-compose.yml` (FastAPI + ChromaDB)
- [ ] Write `Dockerfile` for React frontend (nginx)
- [ ] Set up environment variables (see `09-DEPLOYMENT.md`)
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel
- [ ] Set up custom domain (optional)
- [ ] Configure LangSmith for tracing
- [ ] Set up Sentry for error tracking
- [ ] Load test with 50 concurrent users

---

## Ongoing / Post-launch

- [ ] Add feedback mechanism (thumbs up/down per answer)
- [ ] Fine-tune retrieval based on feedback data
- [ ] Add multilingual query support (Hindi input)
- [ ] Build "Spiritual Growth Roadmap" feature
- [ ] Add guided meditation generator (Baras-anuvekkha based)
- [ ] Explore Sarvam 105B for better Hindi/Sanskrit understanding
