"""Pydantic request/response models for the Jnana Setu API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

# --- Auth -------------------------------------------------------------------


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    tier: Literal["free", "premium", "scholar", "institutional"] = "free"
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    tier: str
    queries_today: int
    daily_limit: int


# --- Query ------------------------------------------------------------------


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    author_filter: list[str] = Field(default_factory=list)
    anuyoga_filter: Optional[str] = None
    language: Literal["en", "hi"] = "en"


class Citation(BaseModel):
    book_id: str
    title: str
    title_hindi: str = ""
    author: str
    anuyoga: str
    chapter: str = "Unknown"
    excerpt: str = ""


# --- Books ------------------------------------------------------------------


class BookSummary(BaseModel):
    id: str
    title: str
    title_hindi: str = ""
    author: str
    author_slug: str
    anuyoga: str
    language: str
    century: str = ""
    total_chunks: int = 0


class BookList(BaseModel):
    total: int
    page: int
    per_page: int
    books: list[BookSummary]


class BookDetail(BookSummary):
    anuyoga_label: str = ""
    description: str = ""
    source_url: str = ""


# --- Authors ----------------------------------------------------------------


class AuthorSummary(BaseModel):
    slug: str
    name: str
    book_count: int
    primary_anuyoga: str = "all_texts"
    era: str = "contemporary"


# --- Daily reflection -------------------------------------------------------


class DailySource(BaseModel):
    title: str
    author: str
    chapter: str = ""


class DailyReflection(BaseModel):
    text: str
    text_translated: str = ""
    reflection: str = ""
    source: DailySource
    generated_at: datetime


# --- Health -----------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    chroma: str
    anthropic: str
    version: str
