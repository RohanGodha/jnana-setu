"""Jnana Setu FastAPI application.

Endpoints (06-API-SPEC.md):
    POST /auth/register
    POST /auth/login
    GET  /auth/me
    POST /query                (SSE stream)
    GET  /books
    GET  /books/{book_id}
    GET  /authors
    POST /daily-reflection
    GET  /health
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import auth
import billing
import catalog
import db
import features
import graph
from config import settings
from models import (
    AuthorSummary,
    BookDetail,
    BookList,
    BookmarkCreate,
    CreateOrderRequest,
    DailyReflection,
    FeedbackCreate,
    HealthResponse,
    LoginRequest,
    MeResponse,
    QueryRequest,
    RegisterRequest,
    SubmitPaymentRequest,
    TokenResponse,
    UserPublic,
)
from fastapi import Body
from retriever import get_retriever

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


# Ensure the schema exists even when the app is imported without the lifespan
# context (e.g. TestClient, some ASGI workers). init_db() is idempotent.
db.init_db()

app = FastAPI(title="Jnana Setu API", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth -------------------------------------------------------------------
@app.post("/auth/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    if db.get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = db.create_user(
        name=body.name,
        email=body.email,
        password_hash=auth.hash_password(body.password),
    )
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = db.get_user_by_email(body.email)
    if not user or not auth.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_access_token(user["id"])
    return TokenResponse(access_token=token, expires_in=settings.jwt_expire_seconds)


@app.get("/auth/me", response_model=MeResponse)
def me(user: dict = Depends(auth.current_user)):
    return MeResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        tier=user["tier"],
        queries_today=db.queries_today(user["id"]),
        daily_limit=auth.effective_limit(user),
        is_admin=auth.is_admin(user),
        is_pro=db.pro_active(user),
        pro_until=user.get("pro_until"),
    )


# --- Query (SSE) ------------------------------------------------------------
def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/query")
def query(body: QueryRequest, user: dict = Depends(auth.current_user)):
    auth.enforce_query_limit(user)
    auth.enforce_hindi_access(user, body.language)

    # Count the query against the daily quota up-front.
    db.increment_queries(user["id"])
    try:
        db.log_history(user["id"], body.query)
    except Exception:
        pass

    is_free = user["tier"] == "free"

    def event_stream():
        try:
            state = graph.prepare(
                query=body.query,
                author_filter=body.author_filter,
                anuyoga_filter=body.anuyoga_filter,
                language=body.language,
            )

            # Scholarly questions with no matching passage get a short nudge.
            # Guidance/crisis still respond (with warmth), so don't short-circuit them.
            if state.get("error") == "no_chunks" and state.get("mode") != "guidance" and not state.get("crisis"):
                msg = "No relevant passages found. Try broadening your question."
                for word in msg.split(" "):
                    yield _sse("token", word + " ")
                yield _sse("citations", [])
                yield _sse("done", {})
                return

            answer_parts: list[str] = []
            for token in graph.stream_answer(state):
                answer_parts.append(token)
                yield _sse("token", token)

            answer = "".join(answer_parts)
            state = graph.hallucination_guard(state, answer)

            citations = state.get("verified_citations", [])
            # Free tier: truncate excerpts to first 100 chars (08-FRONTEND-SPEC.md).
            if is_free:
                citations = [
                    {**c, "excerpt": (c.get("excerpt", "")[:100])} for c in citations
                ]
            yield _sse("citations", citations)
            yield _sse("done", {})
        except Exception as exc:  # stream the error rather than dropping the socket
            yield _sse("error", {"message": str(exc)})
            yield _sse("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- Books ------------------------------------------------------------------
@app.get("/books", response_model=BookList)
def books(
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    anuyoga: str | None = None,
    author_slug: str | None = None,
    language: str | None = None,
    search: str | None = None,
):
    return catalog.list_books(
        page=page,
        per_page=per_page,
        anuyoga=anuyoga,
        author_slug=author_slug,
        language=language,
        search=search,
    )


@app.get("/books/{book_id}", response_model=BookDetail)
def book_detail(book_id: str):
    book = catalog.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


# --- Authors ----------------------------------------------------------------
@app.get("/authors", response_model=list[AuthorSummary])
def authors():
    return catalog.list_authors()


# --- Daily reflection -------------------------------------------------------
@app.post("/daily-reflection", response_model=DailyReflection)
def daily_reflection():
    return catalog.daily_reflection()


# --- Discovery features -----------------------------------------------------
@app.get("/stats")
def stats():
    return features.corpus_stats()


@app.get("/search")
def search_passages(q: str = Query(..., min_length=1, max_length=500),
                    anuyoga: str | None = None, limit: int = Query(8, ge=1, le=20)):
    return {"query": q, "results": features.passage_search(q, anuyoga or "all_texts", None, limit)}


@app.get("/random-sutra")
def random_sutra():
    return features.random_sutra()


@app.get("/books/{book_id}/passages")
def book_passages(book_id: str, limit: int = Query(6, ge=1, le=20)):
    return {"book_id": book_id, "passages": features.book_passages(book_id, limit)}


@app.get("/books/{book_id}/related")
def related_books(book_id: str, limit: int = Query(6, ge=1, le=20)):
    return {"book_id": book_id, "related": features.related_books(book_id, limit)}


@app.get("/suggestions")
def suggestions(prefix: str = ""):
    return {"suggestions": features.suggestions(prefix)}


@app.get("/trending")
def trending():
    return {"trending": db.popular_queries(10)}


# --- Bookmarks --------------------------------------------------------------
@app.post("/bookmarks", status_code=201)
def add_bookmark(body: BookmarkCreate, user: dict = Depends(auth.current_user)):
    return db.add_bookmark(user["id"], body.book_id, body.title, body.author,
                           body.excerpt, body.note)


@app.get("/bookmarks")
def get_bookmarks(user: dict = Depends(auth.current_user)):
    return {"bookmarks": db.list_bookmarks(user["id"])}


@app.delete("/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: str, user: dict = Depends(auth.current_user)):
    if not db.remove_bookmark(user["id"], bookmark_id):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"deleted": bookmark_id}


# --- History / feedback -----------------------------------------------------
@app.get("/history")
def history(user: dict = Depends(auth.current_user)):
    return {"history": db.list_history(user["id"])}


@app.post("/feedback", status_code=201)
def feedback(body: FeedbackCreate, user: dict = Depends(auth.current_user)):
    return db.add_feedback(user["id"], body.query, body.rating, body.comment)


# --- Billing (UPI) ----------------------------------------------------------
@app.get("/billing/plan")
def billing_plan():
    return {
        "plan": "pro",
        "price_inr": settings.pro_price_inr,
        "days": settings.pro_days,
        "upi_configured": bool(settings.upi_vpa),
        "benefits": [
            "Unlimited questions per day",
            "Hindi answers",
            "Full-length source excerpts",
            "Bookmarks & history",
        ],
    }


@app.post("/billing/create-order")
def create_order(body: CreateOrderRequest, user: dict = Depends(auth.current_user)):
    if auth.has_unlimited(user):
        return {"already_pro": True, "message": "You already have full access."}
    amount = settings.pro_price_inr
    pay = db.create_payment(user["id"], amount, body.plan)
    return billing.build_order(pay["id"], amount)


@app.post("/billing/submit")
def submit_payment(body: SubmitPaymentRequest, user: dict = Depends(auth.current_user)):
    if not db.submit_payment_ref(user["id"], body.payment_id, body.txn_ref):
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"status": "pending_approval",
            "message": "Payment reference submitted. Pro unlocks after admin approval."}


@app.get("/billing/my-payments")
def my_payments(user: dict = Depends(auth.current_user)):
    return {"payments": [p for p in db.list_payments() if p["user_id"] == user["id"]]}


# --- Admin ------------------------------------------------------------------
@app.get("/admin/stats")
def admin_stats(admin: dict = Depends(auth.require_admin)):
    return db.counts()


@app.get("/admin/payments")
def admin_payments(status: str | None = None, admin: dict = Depends(auth.require_admin)):
    return {"payments": db.list_payments(status)}


@app.post("/admin/payments/{payment_id}/approve")
def admin_approve(payment_id: str, admin: dict = Depends(auth.require_admin)):
    pay = db.get_payment(payment_id)
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")
    from datetime import datetime, timedelta, timezone
    until = (datetime.now(timezone.utc) + timedelta(days=settings.pro_days)).isoformat()
    db.set_payment_status(payment_id, "paid")
    db.set_pro(pay["user_id"], until, tier="premium")
    return {"approved": payment_id, "user_id": pay["user_id"], "pro_until": until}


@app.post("/admin/payments/{payment_id}/reject")
def admin_reject(payment_id: str, admin: dict = Depends(auth.require_admin)):
    if not db.get_payment(payment_id):
        raise HTTPException(status_code=404, detail="Payment not found")
    db.set_payment_status(payment_id, "rejected")
    return {"rejected": payment_id}


@app.post("/admin/grant-pro/{email}")
def admin_grant_pro(email: str, admin: dict = Depends(auth.require_admin)):
    target = db.get_user_by_email(email)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    from datetime import datetime, timedelta, timezone
    until = (datetime.now(timezone.utc) + timedelta(days=settings.pro_days)).isoformat()
    db.set_pro(target["id"], until, tier="premium")
    return {"granted": email, "pro_until": until}


# --- Health -----------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        chroma=get_retriever().health(),
        anthropic="mock" if settings.mock_mode else "configured",
        version=VERSION,
    )
