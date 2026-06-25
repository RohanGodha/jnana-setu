# API Spec — FastAPI Endpoints

Base URL: `https://api.jnanasetu.com` (prod) / `http://localhost:8000` (dev)

All endpoints return `Content-Type: application/json` unless noted.
Auth endpoints are public. All other endpoints require `Authorization: Bearer <jwt>`.

---

## Auth

### POST /auth/register
```json
// Request
{
  "name": "Rohan Sharma",
  "email": "rohan@example.com",
  "password": "min8chars"
}

// Response 201
{
  "id": "usr_abc123",
  "name": "Rohan Sharma",
  "email": "rohan@example.com",
  "tier": "free",
  "created_at": "2026-06-23T10:00:00Z"
}
```

### POST /auth/login
```json
// Request
{
  "email": "rohan@example.com",
  "password": "min8chars"
}

// Response 200
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

### GET /auth/me
```json
// Response 200
{
  "id": "usr_abc123",
  "name": "Rohan Sharma",
  "email": "rohan@example.com",
  "tier": "free",
  "queries_today": 2,
  "daily_limit": 3
}
```

---

## Query (main RAG endpoint)

### POST /query
*Streams SSE. `Content-Type: text/event-stream`*

```json
// Request
{
  "query": "What does Samayasara say about the nature of the soul?",
  "author_filter": ["vidyasagar", "tarun_sagar"],  // optional, slugs
  "anuyoga_filter": "dravyanuyog",                 // optional
  "language": "en"                                 // "en" | "hi"
}
```

**SSE event stream:**
```
event: token
data: "According"

event: token
data: " to"

event: token
data: " Acharya"

... (streams word by word)

event: citations
data: [
  {
    "book_id": "canonical-012",
    "title": "Samayasara",
    "title_hindi": "समयसार",
    "author": "Acharya Kundakunda",
    "anuyoga": "dravyanuyog",
    "chapter": "Chapter 2 — Jiva Adhikar",
    "excerpt": "The pure soul is distinct from all karma..."
  }
]

event: done
data: {}
```

**Error responses:**
- `401` — Invalid/missing JWT
- `429` — Rate limit exceeded (free tier)
- `422` — Invalid request body

---

## Books catalog

### GET /books
```
Query params:
  page        int     default=1
  per_page    int     default=24, max=100
  anuyoga     string  filter by category
  author_slug string  filter by author
  language    string  "sanskrit"|"hindi"|"english"|"prakrit"
  search      string  full-text search on title
```

```json
// Response 200
{
  "total": 600,
  "page": 1,
  "per_page": 24,
  "books": [
    {
      "id": "canonical-001",
      "title": "Shatkhandagama",
      "title_hindi": "षट्खण्डागम",
      "author": "Acharyas Pushpadanta & Bhutabali",
      "author_slug": "canonical",
      "anuyoga": "dravyanuyog",
      "language": "prakrit",
      "century": "2nd CE",
      "total_chunks": 4823
    }
  ]
}
```

### GET /books/{book_id}
```json
// Response 200
{
  "id": "canonical-001",
  "title": "Shatkhandagama",
  "title_hindi": "षट्खण्डागम",
  "author": "Acharyas Pushpadanta & Bhutabali",
  "author_slug": "canonical",
  "anuyoga": "dravyanuyog",
  "anuyoga_label": "Philosophy & Soul",
  "language": "prakrit",
  "century": "2nd CE",
  "description": "The primary canonical authority on karma theory...",
  "total_chunks": 4823,
  "source_url": "https://jainebooks.org/..."
}
```

---

## Daily reflection

### POST /daily-reflection
*No body required. Returns a random sutra pull.*

```json
// Response 200
{
  "text": "परमाणु पर्याय से लेकर स्कन्ध पर्याय तक...",
  "text_translated": "From the atomic form to the aggregate form...",
  "source": {
    "title": "Panchastikaya-sara",
    "author": "Acharya Kundakunda",
    "chapter": "Pudgala Astikaya"
  },
  "generated_at": "2026-06-23T06:00:00Z"
}
```

---

## Authors

### GET /authors
```json
// Response 200
[
  {
    "slug": "vidyasagar",
    "name": "Acharya Vidyasagar Ji Maharaj",
    "book_count": 50,
    "primary_anuyoga": "dravyanuyog",
    "era": "contemporary"
  },
  ...
]
```

---

## Health

### GET /health
```json
// Response 200
{
  "status": "ok",
  "chroma": "connected",
  "anthropic": "reachable",
  "version": "1.0.0"
}
```
