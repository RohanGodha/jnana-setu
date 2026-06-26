"""Multi-source Jain corpus harvester (beyond archive.org).

Sources:
  - Wikisource  : public-domain Jain sutras/texts via the MediaWiki API
  - GitHub      : repos of Jain texts / bhajans / stavans / stutis (.txt/.md)

Each downloaded text is checked for Jain relevance and de-duplicated by content
hash against everything already in backend/books/, then appended to
data/books.json (ids: wiki-NNNN / gh-NNNN). Set GITHUB_TOKEN to raise GitHub
rate limits.

Usage:
    python harvest_sources.py --wikisource 200 --github 200
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from download_books import (
    BOOKS_DIR, BOOKS_JSON, SESSION, JAIN_KEYWORDS, _detect_anuyoga,
)

WIKI_API = "https://en.wikisource.org/w/api.php"
# Wikimedia requires a descriptive UA and polite rate (<~1 req/s unauth).
WIKI_HEADERS = {"User-Agent": "JnanaSetu-Research/1.0 (https://github.com/jnana-setu; contact: rohan)"}
WIKI_DELAY = 1.5

# Repo meta files that aren't actual texts.
SKIP_FILENAMES = {
    "readme", "license", "licence", "contributing", "changelog", "code_of_conduct",
    "backlog", "todo", "authors", "notice", "security", "index", "package",
    "requirements", "setup", "makefile", "dockerfile", ".gitignore",
}

WIKI_QUERIES = [
    "Jainism", "Jaina", "Jain Sutras", "Tattvartha", "Uttaradhyayana",
    "Acaranga", "Kalpa Sutra", "Mahavira", "Tirthankara", "Jain philosophy",
    "Digambara", "Svetambara", "Jaina literature", "Samayasara", "Ahimsa Jain",
]

GH_QUERIES = [
    "jain sutra", "jainism text", "jain bhajan", "jain stavan", "jain stuti",
    "jain aarti", "namokar mantra", "jain agam", "jain scripture",
    "jain bhakti", "jain pooja", "tirthankar", "jain mantra", "jain stotra",
]

WS = re.compile(r"\s+")


def jain_relevant(text: str) -> bool:
    low = text[:4000].lower()
    return sum(1 for k in JAIN_KEYWORDS if k in low) >= 2


def content_hashes() -> set[str]:
    hashes = set()
    for p in BOOKS_DIR.iterdir():
        if p.is_file() and p.suffix in (".txt", ".md", ".pdf"):
            try:
                hashes.add(hashlib.md5(p.read_bytes()).hexdigest())
            except Exception:
                pass
    return hashes


def gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "JnanaSetu/1.0"}
    tok = os.getenv("GITHUB_TOKEN", "").strip()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def load_books() -> list[dict]:
    return json.loads(BOOKS_JSON.read_text(encoding="utf-8"))


def save_books(books: list[dict]) -> None:
    BOOKS_JSON.write_text(json.dumps(books, ensure_ascii=False, indent=2), encoding="utf-8")


def next_index(books: list[dict], prefix: str) -> int:
    nums = [int(b["id"].split("-")[1]) for b in books if b["id"].startswith(prefix + "-")]
    return (max(nums) + 1) if nums else 1


# --- Wikisource -------------------------------------------------------------
def wiki_plaintext(title: str) -> str:
    try:
        time.sleep(WIKI_DELAY)
        r = SESSION.get(WIKI_API, params={
            "action": "query", "prop": "extracts", "explaintext": 1,
            "titles": title, "format": "json", "redirects": 1,
        }, headers=WIKI_HEADERS, timeout=40)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        for _, pg in pages.items():
            return pg.get("extract", "") or ""
    except Exception:
        return ""
    return ""


def harvest_wikisource(target: int, books: list[dict], seen: set[str]) -> int:
    got = 0
    n = next_index(books, "wiki")
    titles_done: set[str] = set()
    for q in WIKI_QUERIES:
        if got >= target:
            break
        results = None
        for attempt in range(4):
            try:
                time.sleep(WIKI_DELAY)
                r = SESSION.get(WIKI_API, params={
                    "action": "query", "list": "search", "srsearch": q,
                    "srnamespace": 0, "srlimit": 50, "format": "json",
                }, headers=WIKI_HEADERS, timeout=40)
                if r.status_code == 429:
                    raise RuntimeError("429 rate-limited")
                r.raise_for_status()
                results = r.json().get("query", {}).get("search", [])
                break
            except Exception as exc:
                print(f"  wiki search '{q}' attempt {attempt+1}: {exc}; backing off")
                time.sleep(5 * (attempt + 1))
        if results is None:
            continue
        for item in results:
            if got >= target:
                break
            title = item.get("title", "")
            if not title or title in titles_done:
                continue
            titles_done.add(title)
            text = wiki_plaintext(title)
            if len(text) < 500 or not jain_relevant(text):
                continue
            h = hashlib.md5(text.encode("utf-8")).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            bid = f"wiki-{n:04d}"
            dest = BOOKS_DIR / f"{bid}.txt"
            dest.write_text(text, encoding="utf-8")
            books.append({
                "id": bid, "title": title[:200], "title_hindi": "",
                "author": "Wikisource (public domain)", "author_slug": "wikisource",
                "anuyoga": _detect_anuyoga(title + " " + text[:2000]),
                "language": "english", "century": "",
                "source_type": "scripture",
                "source_url": f"https://en.wikisource.org/wiki/{title.replace(' ', '_')}",
                "file_path": f"backend/books/{dest.name}", "total_chunks": 0,
                "description": "Public-domain Jain text from Wikisource.",
            })
            n += 1
            got += 1
            print(f"  [wiki {got}/{target}] {bid} {title[:60]}")
            if got % 20 == 0:
                save_books(books)
            time.sleep(0.3)
    save_books(books)
    return got


# --- GitHub -----------------------------------------------------------------
def harvest_github(target: int, books: list[dict], seen: set[str]) -> int:
    got = 0
    n = next_index(books, "gh")
    repos_done: set[str] = set()
    for q in GH_QUERIES:
        if got >= target:
            break
        try:
            r = SESSION.get("https://api.github.com/search/repositories",
                            params={"q": q, "per_page": 10, "sort": "stars"},
                            headers=gh_headers(), timeout=40)
            if r.status_code != 200:
                print(f"  gh search '{q}' -> {r.status_code}")
                time.sleep(5)
                continue
            repos = r.json().get("items", [])
        except Exception as exc:
            print(f"  gh search '{q}' failed: {exc}")
            continue
        for repo in repos:
            if got >= target:
                break
            full = repo.get("full_name")
            if not full or full in repos_done:
                continue
            repos_done.add(full)
            branch = repo.get("default_branch", "main")
            try:
                tr = SESSION.get(
                    f"https://api.github.com/repos/{full}/git/trees/{branch}",
                    params={"recursive": "1"}, headers=gh_headers(), timeout=40)
                if tr.status_code != 200:
                    continue
                tree = tr.json().get("tree", [])
            except Exception:
                continue
            for node in tree:
                if got >= target:
                    break
                path = node.get("path", "")
                low = path.lower()
                if not (low.endswith(".txt") or low.endswith(".md")):
                    continue
                if Path(low).stem in SKIP_FILENAMES:
                    continue
                if node.get("size", 0) < 300 or node.get("size", 0) > 2_000_000:
                    continue
                raw = f"https://raw.githubusercontent.com/{full}/{branch}/{path}"
                try:
                    resp = SESSION.get(raw, timeout=40)
                    if resp.status_code != 200:
                        continue
                    text = resp.text
                except Exception:
                    continue
                if len(text) < 300 or not jain_relevant(text):
                    continue
                h = hashlib.md5(text.encode("utf-8")).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                bid = f"gh-{n:04d}"
                ext = ".md" if low.endswith(".md") else ".txt"
                dest = BOOKS_DIR / f"{bid}{ext}"
                dest.write_text(text, encoding="utf-8")
                title = Path(path).stem.replace("_", " ").replace("-", " ").title()
                books.append({
                    "id": bid, "title": f"{title}"[:200], "title_hindi": "",
                    "author": f"GitHub: {full}", "author_slug": "github",
                    "anuyoga": _detect_anuyoga(title + " " + text[:2000]),
                    "language": "unknown", "century": "",
                    "source_type": "discourse",
                    "source_url": f"https://github.com/{full}/blob/{branch}/{path}",
                    "file_path": f"backend/books/{dest.name}", "total_chunks": 0,
                    "description": f"Jain text/bhajan harvested from GitHub repo {full}.",
                })
                n += 1
                got += 1
                print(f"  [gh {got}/{target}] {bid} {title[:50]} ({full})")
                if got % 20 == 0:
                    save_books(books)
                time.sleep(0.2)
    save_books(books)
    return got


def main() -> None:
    ap = argparse.ArgumentParser(description="Multi-source Jain harvester")
    ap.add_argument("--wikisource", type=int, default=0)
    ap.add_argument("--github", type=int, default=0)
    args = ap.parse_args()

    BOOKS_DIR.mkdir(exist_ok=True)
    books = load_books()
    seen = content_hashes()
    print(f"existing content hashes: {len(seen)}")

    total = 0
    if args.wikisource:
        print(f"\n== Wikisource (target {args.wikisource}) ==")
        total += harvest_wikisource(args.wikisource, books, seen)
    if args.github:
        print(f"\n== GitHub (target {args.github}) ==")
        total += harvest_github(args.github, books, seen)

    print(f"\nDONE. {total} new texts added from extra sources.")


if __name__ == "__main__":
    main()
