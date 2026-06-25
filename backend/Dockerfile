FROM python:3.11-slim

WORKDIR /app

# System deps for PyMuPDF / sentence-transformers builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Slim runtime deps (no torch); resilient to slow PyPI mirrors.
COPY requirements-docker.txt .
RUN pip install --no-cache-dir --timeout 180 --retries 10 -r requirements-docker.txt

COPY . .

# Persisted ChromaDB volume (built by ingest.py).
VOLUME ["/app/chroma_db"]

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
