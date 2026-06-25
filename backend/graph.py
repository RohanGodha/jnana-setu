"""LangGraph RAG orchestration (02-ARCHITECTURE.md, 03-WORKFLOW.md).

Nodes:
    query_router        -> classify query, set anuyoga + author + language filters
    retrieval_agent     -> hybrid search (dense + sparse + RRF + rerank)
    generator           -> Claude Sonnet (streamed in the API layer)
    hallucination_guard -> Claude Haiku verifies citations are grounded

Because the generator must be *streamed* token-by-token over SSE, the API layer
calls the pipeline in three explicit phases:

    state = prepare(request)          # router + retrieval
    for tok in stream_answer(state):  # generator (streaming)
        ...
    state = guard(state, answer)      # hallucination guard

A fully-compiled LangGraph (``build_graph``) is also provided for non-streaming
runs and tests.
"""
from __future__ import annotations

import json
import re
from typing import Optional, TypedDict

import concepts
import llm
import prompts
from retriever import get_retriever


class RAGState(TypedDict, total=False):
    query: str
    author_filter: list[str]
    anuyoga_filter: str
    language: str
    query_type: str
    mode: str  # "scholarly" | "guidance"
    crisis: bool
    emotional_tone: str
    search_themes: list[str]
    concept_brief: str
    retrieved_chunks: list[dict]
    citations: list[dict]
    raw_answer: str
    verified_answer: str
    verified_citations: list[dict]
    error: Optional[str]


# --- Node: query_router -----------------------------------------------------
def query_router(state: RAGState) -> RAGState:
    query = state["query"]
    try:
        raw = llm.complete(
            prompts.ROUTER_SYSTEM,
            prompts.ROUTER_USER.format(query=query),
            model=None,
            temperature=0.0,
            max_tokens=256,
        )
        data = _safe_json(raw)
    except Exception:
        data = {}

    # --- Intent: scholarly question vs personal life struggle ---------------
    # Heuristics (concepts.py) are a robust floor; the LLM router can upgrade.
    matched = concepts.match_concepts(query)
    heuristic_guidance = concepts.is_guidance(query)
    heuristic_crisis = concepts.detect_crisis(query)

    mode = data.get("mode") or ("guidance" if heuristic_guidance else "scholarly")
    state["mode"] = mode if mode in ("scholarly", "guidance") else "scholarly"
    state["crisis"] = bool(data.get("crisis", False)) or heuristic_crisis
    state["emotional_tone"] = data.get("emotional_tone", "neutral")

    # Search themes: prefer the LLM's, fall back to concept mapping.
    themes = data.get("search_themes") or []
    if not themes and matched:
        themes = [t for c in matched for t in c.search_terms]
    state["search_themes"] = themes
    state["concept_brief"] = concepts.concept_brief(matched)

    # Anuyoga: explicit client filter > LLM > concept mapping > all_texts.
    anuyoga = (
        state.get("anuyoga_filter")
        or data.get("anuyoga")
        or concepts.primary_anuyoga(matched)
        or "all_texts"
    )
    if anuyoga not in prompts.VALID_ANUYOGAS:
        anuyoga = "all_texts"

    state["anuyoga_filter"] = anuyoga
    state["query_type"] = data.get("query_type", "general")
    # Client language preference wins; router language is a fallback.
    state.setdefault("language", data.get("query_language", "en"))
    return state


# --- Node: retrieval_agent --------------------------------------------------
def retrieval_agent(state: RAGState) -> RAGState:
    # In a crisis we skip retrieval and respond with care directly.
    if state.get("crisis"):
        state["retrieved_chunks"] = []
        state["citations"] = []
        return state

    retriever = get_retriever()
    # Expand the query with mapped Jain concepts so retrieval finds the teaching
    # even when the person's words never match the scripture's vocabulary.
    themes = state.get("search_themes") or []
    search_query = state["query"]
    if themes:
        search_query = f"{search_query} {' '.join(themes)}".strip()

    chunks = retriever.hybrid_search(
        query=search_query,
        anuyoga=state.get("anuyoga_filter", "all_texts"),
        author_filter=state.get("author_filter") or [],
    )
    state["retrieved_chunks"] = chunks
    state["citations"] = [_chunk_to_citation(c) for c in chunks]
    if not chunks:
        state["error"] = "no_chunks"
    return state


# --- Node: generator --------------------------------------------------------
def generator(state: RAGState) -> RAGState:
    """Non-streaming generation (used by build_graph / tests)."""
    state["raw_answer"] = "".join(stream_answer(state))
    return state


def _length_directive(query: str) -> tuple[str, int]:
    """Adaptive length: ~80-100 words by default, scaling with how much the user
    shares. Returns (instruction_text, max_tokens)."""
    words = len(query.split())
    if words <= 25:
        lo, hi = 80, 110
    elif words <= 60:
        lo, hi = 120, 180
    elif words <= 120:
        lo, hi = 200, 300
    else:
        lo, hi = 320, 450
    directive = (
        f"\nLENGTH: Keep your reply roughly {lo}-{hi} words — concise and unhurried. "
        "Match the depth the person offered: a brief message gets a brief, focused reply; "
        "a long, detailed one earns a fuller response. Never pad."
    )
    max_tokens = int(hi * 2.2) + 120
    return directive, max_tokens


def stream_answer(state: RAGState):
    """Token generator for the SSE endpoint."""
    # Crisis: respond with care, bypassing retrieval + LLM entirely.
    if state.get("crisis"):
        text = (
            prompts.CRISIS_RESPONSE_HI
            if state.get("language") == "hi"
            else prompts.CRISIS_RESPONSE_EN
        )
        for word in text.split(" "):
            yield word + " "
        return

    chunks = state.get("retrieved_chunks", [])
    length_directive, max_tokens = _length_directive(state["query"])
    is_guidance = state.get("mode") == "guidance"

    if not chunks:
        if is_guidance:
            # Still offer warmth even when no passage matched.
            system = prompts.GUIDANCE_SYSTEM + length_directive
            if state.get("language") == "hi":
                system += "\n" + prompts.HINDI_ADDITION
            user = prompts.GUIDANCE_USER.format(
                query=state["query"],
                concept_brief=state.get("concept_brief", ""),
                context_block="(No directly matching passage was retrieved. Offer "
                "sincere empathy and a humble, general reflection in the Jain spirit, "
                "without inventing citations.)",
            )
            for token in llm.stream(system, user, temperature=0.5, max_tokens=max_tokens):
                yield token
        else:
            yield "No relevant passages found. Try broadening your question."
        return

    context_block = prompts.build_context_block(chunks)

    if is_guidance:
        system = prompts.GUIDANCE_SYSTEM + length_directive
        if state.get("language") == "hi":
            system += "\n" + prompts.HINDI_ADDITION
        user = prompts.GUIDANCE_USER.format(
            query=state["query"],
            concept_brief=state.get("concept_brief", ""),
            context_block=context_block,
        )
        temperature = 0.5
    else:
        system = prompts.GENERATOR_SYSTEM + length_directive
        if state.get("language") == "hi":
            system += "\n" + prompts.HINDI_ADDITION
        user = prompts.GENERATOR_USER.format(
            context_block=context_block, query=state["query"]
        )
        temperature = 0.3

    for token in llm.stream(system, user, temperature=temperature, max_tokens=max_tokens):
        yield token


# --- Node: hallucination_guard ----------------------------------------------
def hallucination_guard(state: RAGState, answer: Optional[str] = None) -> RAGState:
    answer = answer if answer is not None else state.get("raw_answer", "")
    chunks = state.get("retrieved_chunks", [])
    state["verified_answer"] = answer

    if not chunks:
        state["verified_citations"] = []
        return state

    context_block = prompts.build_context_block(chunks)
    try:
        raw = llm.complete(
            prompts.GUARD_SYSTEM,
            prompts.GUARD_USER.format(context_block=context_block, answer=answer),
            model=llm.settings.guard_model_name,
            temperature=0.0,
            max_tokens=512,
        )
        data = _safe_json(raw)
    except Exception:
        data = {}

    grounded = data.get("verified_citations")
    if grounded:
        grounded_keys = {
            _norm(c.get("book", "")) for c in grounded if c.get("grounded", True)
        }
        verified = [
            cit
            for cit in state.get("citations", [])
            if _norm(cit["title"]) in grounded_keys
        ]
        # Never drop everything to nothing if the guard was over-zealous.
        state["verified_citations"] = verified or state.get("citations", [])
    else:
        state["verified_citations"] = state.get("citations", [])
    return state


# --- Phase helpers used by the API layer ------------------------------------
def prepare(
    query: str,
    author_filter: Optional[list[str]] = None,
    anuyoga_filter: Optional[str] = None,
    language: str = "en",
) -> RAGState:
    state: RAGState = {
        "query": query,
        "author_filter": author_filter or [],
        "anuyoga_filter": anuyoga_filter or "",
        "language": language,
    }
    state = query_router(state)
    state = retrieval_agent(state)
    return state


# --- Compiled LangGraph (non-streaming) -------------------------------------
def build_graph():
    """Compile the full pipeline as a LangGraph StateGraph."""
    from langgraph.graph import END, START, StateGraph

    workflow = StateGraph(RAGState)
    workflow.add_node("query_router", query_router)
    workflow.add_node("retrieval_agent", retrieval_agent)
    workflow.add_node("generator", generator)
    workflow.add_node("hallucination_guard", lambda s: hallucination_guard(s))

    workflow.add_edge(START, "query_router")
    workflow.add_edge("query_router", "retrieval_agent")
    workflow.add_conditional_edges(
        "retrieval_agent",
        lambda s: "end" if s.get("error") == "no_chunks" else "generate",
        {"generate": "generator", "end": END},
    )
    workflow.add_edge("generator", "hallucination_guard")
    workflow.add_edge("hallucination_guard", END)
    return workflow.compile()


def run(query: str, **kwargs) -> RAGState:
    """Convenience: run the entire pipeline without streaming."""
    state = prepare(query, **kwargs)
    if state.get("error") == "no_chunks":
        state["verified_answer"] = "No relevant passages found. Try broadening your question."
        state["verified_citations"] = []
        return state
    state = generator(state)
    state = hallucination_guard(state)
    return state


# --- Utils ------------------------------------------------------------------
def _safe_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _chunk_to_citation(chunk: dict) -> dict:
    return {
        "book_id": chunk.get("book_id", chunk.get("id", "")),
        "title": chunk.get("title", "Unknown"),
        "title_hindi": chunk.get("title_hindi", ""),
        "author": chunk.get("author", "Unknown"),
        "anuyoga": chunk.get("anuyoga", "all_texts"),
        "chapter": chunk.get("chapter", "Unknown"),
        "excerpt": (chunk.get("document", "")[:500]).strip(),
    }
