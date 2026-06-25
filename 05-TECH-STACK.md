# Tech Stack — Jnana Setu

## Backend

| Library | Version | Why |
|---------|---------|-----|
| Python | 3.11+ | LangGraph requires 3.10+; 3.11 is fastest |
| FastAPI | 0.111+ | Async, SSE support, Pydantic v2 native |
| LangGraph | 0.2+ | Stateful multi-node RAG pipelines |
| LangChain | 0.2+ | Text splitters, embedding wrappers |
| langchain-anthropic | latest | Claude Sonnet 4.6 integration |
| ChromaDB | 0.5+ | Embeddable vector DB, metadata filtering |
| rank_bm25 | 0.2.2 | BM25 sparse index for hybrid search |
| sentence-transformers | 3.0+ | multilingual-e5-large embeddings |
| PyMuPDF (fitz) | 1.24+ | PDF text extraction |
| BeautifulSoup4 | 4.12+ | HTML parsing |
| python-jose | 3.3+ | JWT auth |
| passlib | 1.7.4 | Password hashing (bcrypt) |
| slowapi | 0.1.9 | Rate limiting middleware |
| uvicorn | 0.29+ | ASGI server |
| pydantic | 2.7+ | Request/response validation |
| python-multipart | 0.0.9 | File upload support |
| openai-whisper | latest | Audio transcription for discourse recordings |

## Embedding model

**Primary:** `intfloat/multilingual-e5-large`
- 560M parameters
- 1024-dim embeddings
- Handles: Hindi, Sanskrit (romanized), English
- IMPORTANT: Prefix queries with `"query: "` and passages with `"passage: "`
- Free, runs locally

**Fallback (if Sanskrit quality is poor):** Sarvam AI embedding API
- Better Sanskrit/Prakrit support
- Paid API

## Re-ranker

`mixedbread-ai/mxbai-rerank-large-v1`
- Cross-encoder re-ranking
- Takes (query, passage) pairs
- Returns relevance scores 0–1
- Run locally via sentence-transformers

## Generator

**Claude Sonnet 4.6** (`claude-sonnet-4-6`)
- Streaming via SSE
- 200k context window (can fit all 8 chunks easily)
- Best balance of quality and speed

**Hallucination guard:** Claude Haiku 4.5
- Cheaper, faster for verification task
- Simple binary: is this citation grounded?

## Frontend

| Library | Version | Why |
|---------|---------|-----|
| React | 18+ | Component model, concurrent features |
| TypeScript | 5+ | Type safety for API contracts |
| Vite | 5+ | Fast HMR, good TS support |
| TailwindCSS | 3.4+ | Utility classes, dark mode easy |
| Zustand | 4+ | Lightweight state management |
| React Router | 6+ | Client-side routing |
| Axios | 1.7+ | HTTP client with interceptors |
| React Query | 5+ | Server state, caching for /books |
| Lucide React | latest | Icon library |

## Infrastructure

| Tool | Purpose |
|------|---------|
| Docker | Containerize FastAPI + ChromaDB |
| Docker Compose | Local dev orchestration |
| Railway | Backend hosting (free tier → paid) |
| Vercel | Frontend hosting (free) |
| LangSmith | LangGraph tracing and eval |
| Sentry | Error tracking (backend + frontend) |

## Dev tools

```
backend/
  requirements.txt
  requirements-dev.txt   ← pytest, black, ruff, mypy

frontend/
  package.json
  .env.local             ← VITE_API_URL
```

## Environment variables

### Backend `.env`
```
ANTHROPIC_API_KEY=sk-ant-...
CHROMA_PERSIST_PATH=./chroma_db
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7
FREE_TIER_DAILY_LIMIT=3
LANGCHAIN_API_KEY=ls-...        # LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=jnana-setu
SENTRY_DSN=https://...
CORS_ORIGINS=http://localhost:5173,https://yourdomain.com
```

### Frontend `.env.local`
```
VITE_API_URL=http://localhost:8000
VITE_SENTRY_DSN=https://...
```
