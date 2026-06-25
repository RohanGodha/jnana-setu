# Architecture — Jnana Setu RAG Chatbot

## System overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                          │
│                    React + Vite + TypeScript                  │
│   Chat UI │ Book Explorer │ Author Filter │ Daily Reflection  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS + SSE
┌──────────────────────▼──────────────────────────────────────┐
│                   FASTAPI BACKEND                            │
│         JWT Auth │ Rate Limit │ CORS │ Pydantic             │
│                                                             │
│  POST /query ──► LangGraph RAG Pipeline                     │
│  GET  /books ──► ChromaDB metadata query                    │
│  POST /daily ──► Random sutra sampler                       │
└──────┬─────────────────────────┬───────────────────────────┘
       │                         │
┌──────▼──────┐         ┌────────▼────────┐
│  CHROMADB   │         │  CLAUDE SONNET  │
│  Vector DB  │         │     4.6 API     │
│             │         │                 │
│ 4 Anuyoga  │         │ Generator +     │
│ collections │         │ Hallucination   │
│ + BM25 idx  │         │ Guard           │
└─────────────┘         └─────────────────┘
```

---

## Component breakdown

### 1. Data layer — `/data/`

```
/data/
  canonical/          ← 50 ancient texts (PDF/TXT)
  acharyas/
    vidyasagar/       ← 50 books
    vidyananda/
    tarun_sagar/
    gyanmati/
    pushpadant_sagar/
    deshbhushan/
    gupti_sagar/
    vardhaman_sagar/
    praman_sagar/
    nirbhay_sagar/
    pulak_sagar/
  transcripts/        ← Whisper output for audio content
  books.json          ← Master catalog (600 entries)
```

**`books.json` schema (single entry):**
```json
{
  "id": "ts-001",
  "title": "Kadve Pravachan (Part 1)",
  "title_hindi": "कड़वे प्रवचन भाग १",
  "author": "Muni Tarun Sagar Ji Maharaj",
  "author_slug": "tarun_sagar",
  "anuyoga": "charananuyog",
  "language": "hindi",
  "century": "21st",
  "source_type": "discourse_transcript",
  "source_url": "https://tarunsagar.in/...",
  "file_path": "data/acharyas/tarun_sagar/kadve-pravachan-1.txt",
  "total_chunks": 0
}
```

---

### 2. Ingestion pipeline — `backend/ingest.py`

```
books.json
    │
    ▼
[Parser] ──── PDF ──► PyMuPDF
           ├── TXT ──► plain read
           └── HTML ──► BeautifulSoup

    │
    ▼
[Cleaner]
  - Remove page headers/footers
  - Normalize Unicode diacritics
  - Remove repetitive publisher boilerplate

    │
    ▼
[Chapter-aware chunker]
  - Split at heading patterns (अध्याय, Chapter, ।।)
  - RecursiveCharacterTextSplitter (512 tok, 64 overlap)
  - Each chunk tagged with: book_id, chapter, page_range

    │
    ▼
[Embedder] ── intfloat/multilingual-e5-large
  - 1024-dim embeddings
  - Batch size: 32
  - Handles Hindi, Sanskrit, English

    │
    ▼
[ChromaDB upsert]
  - collection = anuyoga name
  - document = chunk text
  - metadata = {book_id, author, title, chapter, language, anuyoga}
  - embedding = vector
```

---

### 3. Vector store — ChromaDB

**Collections:**

| Collection | Contents | Approx chunks |
|------------|----------|---------------|
| `dravyanuyog` | Philosophy, soul, karma theory | ~120,000 |
| `charananuyog` | Ethics, conduct, vows | ~80,000 |
| `prathamanuyoga` | Hagiographies, history | ~90,000 |
| `karnanuyoga` | Cosmology, metaphysics | ~60,000 |
| `all_texts` | Everything (for cross-category queries) | ~350,000 |

**Retrieval strategy:**

```python
# Hybrid search: dense + sparse
dense_results  = collection.query(query_embeddings=[q_vec], n_results=20)
sparse_results = bm25_index.get_scores(query_tokens)  # rank_bm25

# Merge with RRF (Reciprocal Rank Fusion)
merged = reciprocal_rank_fusion(dense_results, sparse_results, k=60)

# Re-rank top-20 → keep top-8
reranked = cross_encoder.predict([(query, chunk) for chunk in merged[:20]])
final_chunks = sorted(zip(merged, reranked), key=lambda x: -x[1])[:8]
```

---

### 4. LangGraph pipeline — `backend/graph.py`

```
User query
    │
    ▼
┌─────────────────────┐
│    query_router     │  ← Classifies: philosophical / ethical /
│                     │    hagiographic / cosmological / general
│  Output:            │
│  - anuyoga_filter   │
│  - author_filter    │
│  - query_language   │
└──────────┬──────────┘
           │
    ┌──────▼──────────┐
    │ retrieval_agent  │  ← Hybrid search on correct collection
    │                  │    with optional author metadata filter
    │  Output:         │
    │  - 8 chunks      │
    │  - citations[]   │
    └──────┬───────────┘
           │
    ┌──────▼──────────┐
    │    generator    │  ← Claude Sonnet 4.6
    │                 │    System prompt: Jain philosophy expert
    │  Output:        │    Must cite {title}, {author}, {chapter}
    │  - answer text  │    Answer in query's language
    │  - citations[]  │
    └──────┬──────────┘
           │
    ┌──────▼──────────────┐
    │  hallucination_guard │  ← Second Claude call (haiku for cost)
    │                      │    Verifies each citation exists
    │                      │    Strips hallucinated references
    └──────┬───────────────┘
           │
    ┌──────▼──────┐
    │   Response   │  → FastAPI SSE stream → React
    └─────────────┘
```

**State schema:**
```python
class RAGState(TypedDict):
    query: str
    author_filter: list[str]
    anuyoga_filter: str
    retrieved_chunks: list[dict]
    citations: list[dict]
    raw_answer: str
    verified_answer: str
    verified_citations: list[dict]
    error: str | None
```

---

### 5. FastAPI backend — `backend/`

```
backend/
  main.py           ← FastAPI app, router registration
  graph.py          ← LangGraph pipeline
  retriever.py      ← ChromaDB + BM25 hybrid search
  ingest.py         ← One-time ingestion script
  models.py         ← Pydantic request/response models
  auth.py           ← JWT creation/verification
  middleware.py     ← Rate limiting, CORS
  config.py         ← Settings from env vars
  requirements.txt
```

---

### 6. React frontend — `frontend/`

```
frontend/src/
  pages/
    Home.tsx          ← Daily reflection + quick query CTA
    Chat.tsx          ← Main chat UI
    Books.tsx         ← Book explorer
    Login.tsx         ← Auth page
  components/
    ChatWindow.tsx    ← SSE stream reader + message list
    Message.tsx       ← User / assistant message bubble
    CitationCard.tsx  ← Source book card (title, author, chapter)
    AuthorFilter.tsx  ← Multi-select sidebar (11 Acharyas)
    AnuyogaBadge.tsx  ← Color-coded category pill
    DailyReflection.tsx ← Home screen sutra card
    BookGrid.tsx      ← Searchable book catalog
    BookCard.tsx      ← Single book tile
  store/
    chatStore.ts      ← Zustand: messages, filters, user
  hooks/
    useSSE.ts         ← SSE streaming hook
    useAuth.ts        ← JWT auth hook
  api/
    client.ts         ← Axios instance with auth headers
    endpoints.ts      ← Typed API calls
```

---

## Data flow — query request

```
1. User types question in ChatWindow
2. React: POST /query { query, author_filter[], anuyoga_filter }
3. FastAPI: validates JWT, checks rate limit
4. FastAPI: calls LangGraph pipeline
5. LangGraph: query_router classifies query
6. LangGraph: retrieval_agent fetches 8 chunks from ChromaDB
7. LangGraph: generator streams response from Claude
8. LangGraph: hallucination_guard verifies citations
9. FastAPI: SSE-streams tokens back to React
10. React: ChatWindow renders tokens as they arrive
11. React: CitationCard components appear after full response
```

---

## Security model

| Concern | Solution |
|---------|----------|
| API key exposure | Anthropic key server-side only, never in frontend |
| Auth | JWT (HS256), 7-day expiry |
| Rate limiting | 3 queries/day free, unlimited premium |
| CORS | Whitelist only frontend domain |
| Input sanitization | Pydantic validators on all inputs |
| Prompt injection | System prompt isolation, no raw user text in tool calls |
