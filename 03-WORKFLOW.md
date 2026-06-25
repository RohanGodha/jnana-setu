# Workflow — Jnana Setu RAG Chatbot

## Two distinct workflows

1. **Offline workflow** — runs once (ingestion)
2. **Online workflow** — runs per user query (inference)

---

## Workflow 1 — Offline ingestion

```
START
  │
  ▼
Collect books (PDF/TXT/HTML/Audio)
  │
  ├──► Audio files ──► Whisper transcription ──► .txt
  │
  ▼
For each book in books.json:
  │
  ├── 1. Parse raw text (PyMuPDF / plain read)
  │
  ├── 2. Clean text
  │        remove headers, footers, page numbers
  │        normalize Unicode (Sanskrit diacritics)
  │        strip publisher boilerplate
  │
  ├── 3. Detect chapter boundaries
  │        regex: r'(Chapter|अध्याय|Adhyay|।।\s*\d+\s*।।)'
  │        tag each segment with chapter number
  │
  ├── 4. Chunk with overlap
  │        RecursiveCharacterTextSplitter
  │        chunk_size=512, overlap=64
  │        separators=["\n\n", "\n", "।", " "]
  │
  ├── 5. Build metadata payload per chunk
  │        {
  │          book_id, title, author, author_slug,
  │          anuyoga, language, chapter, page_range,
  │          chunk_index, source_type
  │        }
  │
  ├── 6. Embed chunk text
  │        model: intfloat/multilingual-e5-large
  │        prefix: "passage: " + chunk_text  (e5 requires this)
  │
  └── 7. Upsert to ChromaDB
           collection = chunk.anuyoga
           id = f"{book_id}_{chunk_index}"
           document = chunk_text
           embedding = vector
           metadata = payload

END — Build BM25 index from all documents (rank_bm25)
```

**Expected time:** 4–8 hours for 600 books on a modern laptop.
**Output:** ~350,000 chunks across 4 collections + BM25 index.

---

## Workflow 2 — Online query (per request)

### Step-by-step

```
User input: "What does Samayasara say about the nature of the soul?"
Optional filters: author=["vidyasagar"], anuyoga="dravyanuyog"

STEP 1 — Query routing (LangGraph node: query_router)
──────────────────────────────────────────────────────
  Input : raw query + filters
  Action: LLM call to classify query type
  Output: {
    anuyoga_collection: "dravyanuyog",
    effective_author_filter: ["vidyasagar"] or None,
    query_language: "english",
    query_type: "philosophical"
  }

STEP 2 — Hybrid retrieval (LangGraph node: retrieval_agent)
────────────────────────────────────────────────────────────
  2a. Embed query with prefix "query: " + query_text
  2b. Dense search: ChromaDB cosine similarity, top-20
      with metadata filter: where={"author_slug": {"$in": ["vidyasagar"]}}
  2c. Sparse search: BM25 on query tokens, top-20
  2d. Merge: Reciprocal Rank Fusion (k=60)
  2e. Re-rank: mxbai-rerank-large-v1 cross-encoder, keep top-8
  Output: 8 chunks with metadata

STEP 3 — Response generation (LangGraph node: generator)
─────────────────────────────────────────────────────────
  Input : query + 8 chunks
  Model : claude-sonnet-4-6
  Stream: Yes (SSE)
  System prompt: (see 07-PROMPTS.md)
  Output: answer text with inline citations like [Samayasara, Ch.2]

STEP 4 — Hallucination guard (LangGraph node: hallucination_guard)
────────────────────────────────────────────────────────────────────
  Model : claude-haiku-4-5 (cheaper for this verification task)
  Input : answer + retrieved chunks
  Check : Does each citation appear in the retrieved chunks?
  Action: Strip any citation not grounded in the context
  Output: verified_answer, verified_citations[]

STEP 5 — SSE stream to client
──────────────────────────────
  FastAPI yields tokens as they arrive from Claude
  Final event: {type: "citations", data: verified_citations[]}
  Client renders tokens → then appends citation cards
```

---

## Query routing logic

The router uses a short LLM call to classify the query into one of these buckets:

| Query type | Anuyoga collection | Example query |
|------------|-------------------|---------------|
| Philosophical / soul / karma | `dravyanuyog` | "What is the nature of the jiva?" |
| Ethics / vows / householder | `charananuyog` | "How should a shravaka observe Paryushana?" |
| Life stories / Tirthankaras | `prathamanuyoga` | "Tell me about Parshvanatha's life" |
| Cosmology / universe / time | `karnanuyoga` | "Describe the structure of Jambudvipa" |
| General / unclear | `all_texts` | "Tell me about Jainism" |

---

## Author filter behavior

When an author filter is set:
- ChromaDB `where` clause filters to only that author's chunks
- If <3 results found, fallback: expand to same Anuyoga collection without author filter
- Citation cards will always show the actual author of the source, never fabricated

When no author filter:
- Searches `all_texts` or the classified Anuyoga collection
- Returns the best-matching chunks regardless of author

---

## Error handling

| Scenario | Behavior |
|----------|----------|
| No chunks retrieved | Return: "No relevant passages found. Try broadening your question." |
| Claude API timeout | Retry once, then stream error message |
| Hallucination guard removes all citations | Return answer with warning: "Sources could not be verified" |
| Rate limit exceeded (free tier) | Return 429 with message: "Daily limit reached. Upgrade for unlimited access." |
| Invalid JWT | Return 401, React redirects to /login |

---

## Latency budget

| Step | Target latency |
|------|---------------|
| Query routing | ~500ms |
| Hybrid retrieval | ~300ms |
| Re-ranking | ~400ms |
| First token from Claude | ~800ms |
| Full response (avg 300 words) | ~4–6s total |
| Hallucination guard | ~600ms (parallel with streaming) |
| **Total TTFB** | **~1.5s** |
| **Total completion** | **~6–8s** |
