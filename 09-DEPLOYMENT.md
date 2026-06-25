# Deployment — Jnana Setu

## Local development

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker Desktop (for ChromaDB container option)

### Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and fill env vars
cp .env.example .env

# Run ingestion (ONCE — takes hours)
python ingest.py

# Start dev server
uvicorn main:app --reload --port 8000
```

### Frontend setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Set VITE_API_URL=http://localhost:8000
npm run dev   # → http://localhost:5173
```

---

## Docker setup

### `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ChromaDB persisted volume
VOLUME ["/app/chroma_db"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml`
```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/app/chroma_db
      - ./data:/app/data:ro      # book files (read-only)
    env_file:
      - ./backend/.env
    depends_on:
      - chromadb

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:8000

volumes:
  chroma_data:
```

### `frontend/Dockerfile`
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

### `frontend/nginx.conf`
```nginx
events {}
http {
  include mime.types;
  server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
      try_files $uri $uri/ /index.html;  # SPA routing
    }

    location /api/ {
      proxy_pass http://backend:8000/;
    }
  }
}
```

---

## Railway deployment (backend)

1. Push code to GitHub
2. New project → Deploy from GitHub
3. Select `backend/` as root
4. Add environment variables (copy from `.env`)
5. Add a volume: `/app/chroma_db`

**Important:** Run ingestion locally first, then upload the `chroma_db/` folder to a Railway volume or use a mounted persistent disk.

Alternatively: Run ingestion as a one-time Railway job before starting the main service.

```bash
# Upload chroma_db to Railway volume via CLI
railway run python ingest.py
```

---

## Vercel deployment (frontend)

```bash
npm install -g vercel
cd frontend
vercel deploy --prod
# Set VITE_API_URL to your Railway backend URL
```

---

## Environment variables checklist

### Backend (Railway secrets)
```
ANTHROPIC_API_KEY          ← from console.anthropic.com
JWT_SECRET                 ← generate: openssl rand -hex 32
LANGCHAIN_API_KEY          ← from smith.langchain.com
LANGCHAIN_TRACING_V2       ← true
LANGCHAIN_PROJECT          ← jnana-setu
SENTRY_DSN                 ← from sentry.io
CORS_ORIGINS               ← https://jnanasetu.vercel.app
FREE_TIER_DAILY_LIMIT      ← 3
CHROMA_PERSIST_PATH        ← /app/chroma_db
```

### Frontend (Vercel env)
```
VITE_API_URL               ← https://jnana-setu.railway.app
VITE_SENTRY_DSN            ← from sentry.io
```

---

## Post-deployment checklist

- [ ] `/health` endpoint returns 200
- [ ] Test one query end-to-end
- [ ] Verify SSE streaming works (not just HTTP/2 push)
- [ ] Test auth flow (register → login → query)
- [ ] Test rate limiting (free tier, 4th query should 429)
- [ ] LangSmith dashboard shows traces
- [ ] Sentry captures a test error
- [ ] CORS allows frontend domain only
