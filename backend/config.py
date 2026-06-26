"""Application settings loaded from environment variables.

Uses pydantic-settings so that a missing ``.env`` is fine for tests/CI.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

# OpenAI-compatible base URLs + sensible default models per provider.
# Groq and Gemini have generous free tiers; DeepSeek/OpenAI are paid.
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "anthropic": {
        "base_url": "",  # uses the native Anthropic SDK
        "gen": "claude-sonnet-4-6",
        "guard": "claude-haiku-4-5",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "gen": "llama-3.3-70b-versatile",
        "guard": "llama-3.1-8b-instant",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gen": "gemini-2.0-flash",
        "guard": "gemini-2.0-flash-lite",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "gen": "deepseek-chat",
        "guard": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "gen": "gpt-4o-mini",
        "guard": "gpt-4o-mini",
    },
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider ---
    # "mock" | "anthropic" | "groq" | "gemini" | "deepseek" | "openai"
    llm_provider: str = "mock"
    llm_api_key: str = ""           # key for the chosen provider
    llm_base_url: str = ""          # optional override of the preset base URL
    generator_model: str = ""       # empty -> provider preset default
    guard_model: str = ""           # empty -> provider preset default

    # Back-compat: if set, implies the Anthropic provider.
    anthropic_api_key: str = ""

    # --- Vector store ---
    chroma_persist_path: str = str(BASE_DIR / "chroma_db")
    # "chroma" (local embedded) | "qdrant" (hosted, off-disk/off-RAM)
    vector_backend: str = "chroma"
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "jnana_setu"
    # Coarser chunking keeps the hosted vector count within free-tier limits.
    ingest_chunk_size: int = 512
    ingest_chunk_overlap: int = 64

    # --- Embeddings / rerank ---
    embedding_backend: str = "hash"  # "e5" | "hash"
    embedding_model: str = "intfloat/multilingual-e5-large"
    rerank_enabled: bool = False
    rerank_model: str = "mixedbread-ai/mxbai-rerank-large-v1"

    # --- Retrieval ---
    dense_top_k: int = 20
    sparse_top_k: int = 20
    rrf_k: int = 60
    final_top_k: int = 8

    # --- Auth ---
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # --- Tiers ---
    free_tier_daily_limit: int = 3

    # --- Admin + monetization (UPI) ---
    admin_email: str = ""            # this account gets full/free/unlimited access
    upi_vpa: str = ""                # your UPI ID to receive payments (e.g. name@okhdfcbank)
    upi_payee_name: str = "Jnana Setu"
    pro_price_inr: int = 199         # price of the Pro plan
    pro_days: int = 30               # Pro validity per payment

    # --- Storage ---
    user_db_path: str = str(BASE_DIR / "jnana_setu.db")
    books_json: str = str(BASE_DIR.parent / "data" / "books.json")

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Observability ---
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_project: str = "jnana-setu"
    sentry_dsn: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- Provider resolution ------------------------------------------------
    @property
    def provider(self) -> str:
        """Normalized provider. Falls back to anthropic if only the legacy key is set."""
        p = (self.llm_provider or "").strip().lower()
        if p in ("", "mock") and self.anthropic_api_key.strip():
            return "anthropic"
        return p or "mock"

    @property
    def api_key(self) -> str:
        if self.provider == "anthropic":
            return (self.anthropic_api_key or self.llm_api_key).strip()
        return self.llm_api_key.strip()

    @property
    def base_url(self) -> str:
        if self.llm_base_url.strip():
            return self.llm_base_url.strip()
        return PROVIDER_PRESETS.get(self.provider, {}).get("base_url", "")

    @property
    def gen_model(self) -> str:
        if self.generator_model.strip():
            return self.generator_model.strip()
        return PROVIDER_PRESETS.get(self.provider, {}).get("gen", "")

    @property
    def guard_model_name(self) -> str:
        if self.guard_model.strip():
            return self.guard_model.strip()
        return PROVIDER_PRESETS.get(self.provider, {}).get("guard", self.gen_model)

    @property
    def mock_mode(self) -> bool:
        """No usable provider/key -> deterministic mock so the app works offline."""
        return self.provider == "mock" or not self.api_key

    @property
    def jwt_expire_seconds(self) -> int:
        return self.jwt_expire_days * 24 * 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
