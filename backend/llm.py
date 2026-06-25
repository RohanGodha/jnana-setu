"""LLM wrapper supporting multiple providers + an offline MOCK mode.

Providers (set via LLM_PROVIDER):
- ``mock``      : deterministic, no network/spend — the whole RAG pipeline still works.
- ``anthropic`` : native Anthropic SDK (Claude).
- ``groq`` / ``gemini`` / ``deepseek`` / ``openai`` : OpenAI-compatible chat API
  (Groq & Gemini have free tiers).

When no API key is configured the app falls back to mock mode so it always runs.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Iterator, Optional

from config import settings


# --- Provider clients -------------------------------------------------------
@lru_cache
def _anthropic():
    from anthropic import Anthropic

    return Anthropic(api_key=settings.api_key)


@lru_cache
def _openai_compatible():
    """One client for Groq / Gemini / DeepSeek / OpenAI (all OpenAI-compatible)."""
    from openai import OpenAI

    return OpenAI(api_key=settings.api_key, base_url=settings.base_url or None)


def _gen_model(model: Optional[str]) -> str:
    return model or settings.gen_model


# --- Non-streaming completion ----------------------------------------------
def complete(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> str:
    if settings.mock_mode:
        return _mock_complete(system, user)

    if settings.provider == "anthropic":
        resp = _anthropic().messages.create(
            model=_gen_model(model),
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            b.text for b in resp.content if getattr(b, "type", "") == "text"
        )

    resp = _openai_compatible().chat.completions.create(
        model=_gen_model(model),
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


# --- Streaming completion ---------------------------------------------------
def stream(
    system: str,
    user: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Iterator[str]:
    if settings.mock_mode:
        yield from _mock_stream(system, user)
        return

    if settings.provider == "anthropic":
        with _anthropic().messages.stream(
            model=_gen_model(model),
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": user}],
        ) as s:
            for text in s.text_stream:
                yield text
        return

    completion = _openai_compatible().chat.completions.create(
        model=_gen_model(model),
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    for chunk in completion:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# --- Mock implementations ---------------------------------------------------
def _extract_sources(user: str) -> list[dict]:
    """Parse the SOURCE block built by prompts.build_context_block."""
    sources = []
    blocks = re.split(r"\n-+\n", user)
    for block in blocks:
        if "Book:" not in block:
            continue
        title = _grab(block, "Book")
        author = _grab(block, "Author")
        chapter = _grab(block, "Chapter")
        text_match = re.search(r"Text:\n(.*)", block, re.DOTALL)
        text = (text_match.group(1).strip() if text_match else "")
        if title:
            sources.append(
                {"title": title, "author": author, "chapter": chapter, "text": text}
            )
    return sources


def _grab(block: str, label: str) -> str:
    m = re.search(rf"{label}:\s*(.+)", block)
    return m.group(1).strip() if m else ""


def _extract_question(user: str) -> str:
    # Guidance prompt: the message is the first quoted line.
    m = re.search(r'shared this with you:\s*\n+"(.*?)"', user, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"USER QUESTION:\n(.*?)\n\n", user, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:Query|Message):\s*(.+)", user)
    return m.group(1).strip() if m else ""


def _mock_complete(system: str, user: str) -> str:
    # Router -> JSON classification (now intent-aware)
    if "perceptive listener" in system or "Classify the user's query" in system:
        import concepts

        q = _extract_question(user)
        anuyoga, qtype = _classify_heuristic(q.lower())
        lang = "hi" if re.search(r"[\u0900-\u097F]", q) else "en"
        matched = concepts.match_concepts(q)
        crisis = concepts.detect_crisis(q)
        guidance = crisis or concepts.is_guidance(q)
        themes = [t for c in matched for t in c.search_terms]
        if matched:
            anuyoga = matched[0].anuyoga
        return json.dumps(
            {
                "mode": "guidance" if guidance else "scholarly",
                "crisis": crisis,
                "emotional_tone": (matched[0].key if matched else "neutral"),
                "anuyoga": anuyoga,
                "query_type": qtype,
                "search_themes": themes,
                "query_language": lang,
                "confidence": 0.55,
                "reasoning": "Heuristic classification (mock mode).",
            }
        )
    # Guard -> mark everything present as grounded
    if "fact-checker" in system:
        sources = _extract_sources(user)
        verified = [
            {
                "book": s["title"],
                "author": s["author"],
                "chapter": s["chapter"],
                "grounded": True,
            }
            for s in sources
        ]
        return json.dumps(
            {
                "verified": True,
                "verified_citations": verified,
                "unverified_citations": [],
                "safe_to_serve": True,
            }
        )
    # Default: assemble an answer from the sources
    return "".join(_mock_stream(system, user))


def _is_guidance_prompt(system: str) -> bool:
    # Markers unique to GUIDANCE_SYSTEM that don't span line breaks.
    return "FIRST, SEE THEM" in system or "compassionate guide" in system


def _target_words(system: str) -> Optional[int]:
    """Read the adaptive LENGTH directive injected by graph._length_directive."""
    m = re.search(r"roughly\s+\d+-(\d+)\s+words", system)
    return int(m.group(1)) if m else None


_MOCK_NOTE = "(Mock mode - set LLM_PROVIDER + LLM_API_KEY for full LLM responses.)"


def _emit_capped(text: str, target: Optional[int]) -> Iterator[str]:
    """Stream word-by-word, approximately honoring the target length so the mock
    reflects the same adaptive-length behavior Claude follows from the prompt."""
    words = text.split(" ")
    if target and len(words) > target:
        words = words[:target]
        # Close cleanly on a sentence-ish boundary, then append the note.
        words[-1] = words[-1].rstrip(",;") + "."
        words.append(_MOCK_NOTE)
    else:
        words.append(_MOCK_NOTE)
    for w in words:
        if w:
            yield w + " "


def _mock_stream(system: str, user: str) -> Iterator[str]:
    sources = _extract_sources(user)
    question = _extract_question(user)
    target = _target_words(system)

    if _is_guidance_prompt(system):
        yield from _emit_capped(_mock_guidance_text(question, sources), target)
        return

    if not sources:
        yield from _emit_capped(
            "No relevant passages were found for this question. "
            "Try broadening your query or removing the author filter.",
            None,
        )
        return

    primary = sources[0]
    parts = [
        f'On the question of "{question}", the tradition offers a clear teaching.',
        f"{primary['text'][:220].strip()} "
        f"[{primary['title']}, {primary['author']}, {primary['chapter']}].",
    ]
    if len(sources) > 1:
        s2 = sources[1]
        parts.append(
            f"This is reinforced elsewhere: {s2['text'][:160].strip()} "
            f"[{s2['title']}, {s2['author']}, {s2['chapter']}]."
        )
    parts.append(
        "In essence, the soul (jiva) is to be understood through the lens of these "
        "passages, and a sincere seeker is encouraged to contemplate them directly."
    )
    yield from _emit_capped(" ".join(parts), target)


def _mock_guidance_text(question: str, sources: list[dict]) -> str:
    """Empathy-first, guru-style mock reply assembled from retrieved teachings."""
    parts = [
        "I hear you, and I want you to know that what you're carrying is real - "
        "thank you for trusting me with it.",
    ]
    if sources:
        primary = sources[0]
        parts.append(
            f"The tradition meets this gently. {primary['text'][:200].strip()} "
            f"[{primary['title']}, {primary['author']}, {primary['chapter']}]."
        )
        if len(sources) > 1:
            s2 = sources[1]
            parts.append(
                f"And it reminds us: {s2['text'][:140].strip()} "
                f"[{s2['title']}, {s2['author']}, {s2['chapter']}]."
            )
        parts.append(
            "None of this is your true self; the disturbance is passing, while the "
            "soul that watches it remains whole."
        )
    else:
        parts.append(
            "Even without a single verse before us, the Jain spirit would simply sit "
            "with you here, unhurried, and remind you that this storm is not your essence."
        )
    parts.append(
        "For today, try one small step: before you react, pause for three slow breaths "
        "and silently offer forgiveness - to them, and to yourself."
    )
    return " ".join(parts)


def _classify_heuristic(q: str) -> tuple[str, str]:
    rules = [
        (("soul", "jiva", "karma", "moksha", "liberation", "substance", "dravya",
          "logic", "anekant", "syadvad"), "dravyanuyog", "philosophical"),
        (("vow", "vrat", "conduct", "ethic", "fast", "paryushana", "shravaka",
          "meditation", "samayik", "householder"), "charananuyog", "ethical"),
        (("life", "biography", "tirthankara", "mahavira", "parshva", "purana",
          "story", "rishabh"), "prathamanuyoga", "biographical"),
        (("cosmos", "universe", "jambudvipa", "loka", "time cycle", "astronom",
          "geograph"), "karnanuyoga", "cosmological"),
    ]
    for keywords, anuyoga, qtype in rules:
        if any(k in q for k in keywords):
            return anuyoga, qtype
    return "all_texts", "general"
