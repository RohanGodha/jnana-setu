"""Download corpus books from the Internet Archive (archive.org).

For every entry in ``data/books.json`` this script:
  1. searches archive.org (mediatype:texts) for the title (+ author hint),
  2. scores candidates by title/author token overlap and keeps the best match
     above a relevance threshold,
  3. downloads a usable file -- preferring the small OCR'd ``*_djvu.txt`` text
     (exactly what ingest.py needs), falling back to the largest PDF,
  4. saves it to ``backend/books/<book_id>.<ext>`` and records the relative
     ``file_path`` back into books.json.

Only freely/publicly hosted Internet Archive items are fetched. Items behind
lending/restriction are skipped. The script is resumable (skips books that
already have a downloaded file) and polite (throttled requests + retries).

Usage:
    python download_books.py                 # try every catalog entry
    python download_books.py --limit 60      # only first N entries
    python download_books.py --only canonical # only ids starting with prefix
    python download_books.py --min-score 2   # relevance threshold (default 2)
    python download_books.py --prefer pdf    # prefer pdf over text
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

try:  # ensure Unicode-safe console output on Windows (cp1252)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
BOOKS_DIR = BASE_DIR / "books"
BOOKS_JSON = BASE_DIR.parent / "data" / "books.json"

SEARCH_URL = "https://archive.org/advancedsearch.php"
SCRAPE_URL = "https://archive.org/services/search/v1/scrape"
META_URL = "https://archive.org/metadata/{identifier}"
DL_URL = "https://archive.org/download/{identifier}/{filename}"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "JnanaSetu-CorpusBot/1.0 (research; contact: rohan)"})

STOPWORDS = {
    "the", "of", "and", "a", "an", "in", "to", "ji", "maharaj", "vol",
    "part", "collected", "works", "shri", "sri", "acharya", "muni",
    "aryika", "mataji", "upadhyay", "swami", "commentary", "on",
}


def tokens(text: str) -> set[str]:
    text = re.sub(r"[\(\)\[\]\-_,.:]", " ", text.lower())
    return {t for t in text.split() if len(t) > 2 and t not in STOPWORDS}


def clean_title(title: str) -> str:
    # Drop parenthetical qualifiers and volume markers for searching.
    title = re.sub(r"\([^)]*\)", " ", title)
    title = re.sub(r"\b(Vol\.?|Part)\s*\d+\b", " ", title, flags=re.I)
    return re.sub(r"\s+", " ", title).strip()


def search(query: str, rows: int = 8) -> list[dict]:
    params = {
        "q": f'({query}) AND mediatype:texts',
        "fl[]": ["identifier", "title", "creator", "language", "downloads"],
        "rows": rows,
        "output": "json",
    }
    for attempt in range(3):
        try:
            r = SESSION.get(SEARCH_URL, params=params, timeout=40)
            r.raise_for_status()
            return r.json().get("response", {}).get("docs", [])
        except Exception:
            time.sleep(2 * (attempt + 1))
    return []


def as_text(value) -> str:
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value or "")


def score_candidate(book: dict, doc: dict) -> float:
    """Relevance score. Rewards title coverage; distinctive long terms count
    extra so rare single-word Sanskrit titles still match strongly."""
    want = tokens(clean_title(book["title"]))
    if not want:
        return 0.0
    got = tokens(as_text(doc.get("title")))
    matched = want & got
    if not matched:
        return 0.0
    coverage = len(matched) / len(want)            # fraction of title found
    distinctive = any(len(t) >= 6 for t in matched)  # rare term present
    score = coverage * 2 + len(matched)            # base
    if distinctive:
        score += 1
    # Bonus when the author matches too.
    author_want = tokens(book.get("author", ""))
    author_got = tokens(as_text(doc.get("creator")))
    if author_want & author_got:
        score += 1
    # Require at least half the title words OR a distinctive term.
    if coverage < 0.5 and not distinctive:
        return 0.0
    return score


def pick_file(identifier: str, prefer: str) -> tuple[str, str] | None:
    """Return (filename, ext) of best downloadable file, or None."""
    try:
        r = SESSION.get(META_URL.format(identifier=identifier), timeout=40)
        r.raise_for_status()
        meta = r.json()
    except Exception:
        return None

    # Respect access restrictions (lending / no public download).
    md = meta.get("metadata", {})
    if str(md.get("access-restricted-item", "")).lower() == "true":
        return None

    files = meta.get("files", [])
    txt_files, pdf_files = [], []
    for f in files:
        name = f.get("name", "")
        size = int(f.get("size", 0) or 0)
        low = name.lower()
        if low.endswith("_djvu.txt") or (low.endswith(".txt") and "_djvu" in low):
            txt_files.append((size, name))
        elif low.endswith(".txt") and not low.endswith("_meta.txt"):
            txt_files.append((size, name))
        elif low.endswith(".pdf"):
            pdf_files.append((size, name))

    order = (pdf_files, txt_files) if prefer == "pdf" else (txt_files, pdf_files)
    for group in order:
        if group:
            group.sort(reverse=True)  # largest first
            name = group[0][1]
            ext = ".txt" if name.lower().endswith(".txt") else ".pdf"
            return name, ext
    return None


def download(identifier: str, filename: str, dest: Path) -> bool:
    url = DL_URL.format(identifier=identifier, filename=filename)
    for attempt in range(3):
        try:
            with SESSION.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with tmp.open("wb") as fh:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        if chunk:
                            fh.write(chunk)
                tmp.replace(dest)
            return dest.stat().st_size > 0
        except Exception as exc:
            if attempt == 2:
                print(f"    ! download failed: {exc}")
                return False
            time.sleep(2 * (attempt + 1))
    return False


GH_TOKEN_ENV = "GITHUB_TOKEN"


def _gh_headers() -> dict:
    import os
    h = {"Accept": "application/vnd.github+json",
         "User-Agent": "JnanaSetu-CorpusBot/1.0"}
    tok = os.getenv(GH_TOKEN_ENV, "").strip()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def github_fallback(book: dict, book_id: str) -> tuple[Path, str] | None:
    """Search GitHub repositories for a file matching the book title and
    download a raw .txt/.pdf if found. Best-effort; unauthenticated GitHub
    search is heavily rate-limited (set GITHUB_TOKEN to improve results)."""
    want = tokens(clean_title(book["title"]))
    if not want:
        return None
    q = clean_title(book["title"])
    try:
        r = SESSION.get(
            "https://api.github.com/search/repositories",
            params={"q": f"{q} jain", "per_page": 5},
            headers=_gh_headers(), timeout=30,
        )
        if r.status_code != 200:
            return None
        repos = r.json().get("items", [])
    except Exception:
        return None

    for repo in repos:
        full = repo.get("full_name")
        branch = repo.get("default_branch", "main")
        try:
            tr = SESSION.get(
                f"https://api.github.com/repos/{full}/git/trees/{branch}",
                params={"recursive": "1"}, headers=_gh_headers(), timeout=30,
            )
            if tr.status_code != 200:
                continue
            tree = tr.json().get("tree", [])
        except Exception:
            continue

        best_path, best_overlap = None, 0
        for node in tree:
            path = node.get("path", "")
            low = path.lower()
            if not (low.endswith(".txt") or low.endswith(".pdf") or low.endswith(".md")):
                continue
            overlap = len(want & tokens(Path(path).stem))
            if overlap > best_overlap:
                best_path, best_overlap = path, overlap

        if best_path and best_overlap >= max(1, len(want) // 2):
            ext = ".txt" if not best_path.lower().endswith(".pdf") else ".pdf"
            raw = f"https://raw.githubusercontent.com/{full}/{branch}/{best_path}"
            dest = BOOKS_DIR / f"{book_id}{ext}"
            try:
                with SESSION.get(raw, stream=True, timeout=90) as resp:
                    resp.raise_for_status()
                    tmp = dest.with_suffix(dest.suffix + ".part")
                    with tmp.open("wb") as fh:
                        for chunk in resp.iter_content(1 << 16):
                            if chunk:
                                fh.write(chunk)
                    tmp.replace(dest)
                if dest.stat().st_size > 0:
                    return dest, f"https://github.com/{full}/blob/{branch}/{best_path}"
            except Exception:
                continue
    return None


def already_downloaded(book_id: str) -> Path | None:
    for ext in (".txt", ".pdf"):
        p = BOOKS_DIR / f"{book_id}{ext}"
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def run(limit: int | None, only: str | None, min_score: int, prefer: str) -> None:
    BOOKS_DIR.mkdir(exist_ok=True)
    books = json.loads(BOOKS_JSON.read_text(encoding="utf-8"))

    targets = [b for b in books if not only or b["id"].startswith(only)]
    if limit:
        targets = targets[:limit]

    found = skipped = failed = 0
    print(f"Attempting {len(targets)} books -> {BOOKS_DIR}\n")

    for i, book in enumerate(targets, 1):
        bid, title = book["id"], book["title"]
        existing = already_downloaded(bid)
        if existing:
            book["file_path"] = f"backend/books/{existing.name}"
            found += 1
            print(f"[{i}/{len(targets)}] {bid} {title}: already have {existing.name}")
            continue

        # Skip auto-generated placeholder titles (no real source to find).
        if re.search(r"Collected Works Vol\. \d+", title):
            skipped += 1
            print(f"[{i}/{len(targets)}] {bid} {title}: placeholder, skipped")
            continue

        query = f'title:({clean_title(title)})'
        docs = search(query)
        # Rank all candidates above threshold, best first.
        ranked = sorted(
            ((score_candidate(book, d), d) for d in docs),
            key=lambda x: x[0], reverse=True,
        )
        ranked = [(s, d) for s, d in ranked if s >= min_score]

        got_it = False
        for s, doc in ranked[:5]:  # try up to 5 candidates (recover restricted)
            identifier = doc["identifier"]
            picked = pick_file(identifier, prefer)
            if not picked:
                continue
            filename, ext = picked
            dest = BOOKS_DIR / f"{bid}{ext}"
            print(f"[{i}/{len(targets)}] {bid} {title}: {identifier} -> {filename}")
            if download(identifier, filename, dest):
                book["file_path"] = f"backend/books/{dest.name}"
                book["source_url"] = f"https://archive.org/details/{identifier}"
                found += 1
                got_it = True
                break

        if not got_it:
            # Fallback: try GitHub for a raw text/pdf of this title.
            gh = github_fallback(book, bid)
            if gh:
                book["file_path"] = f"backend/books/{gh[0].name}"
                book["source_url"] = gh[1]
                found += 1
                print(f"[{i}/{len(targets)}] {bid} {title}: GitHub -> {gh[1]}")
            else:
                failed += 1
                why = "no archive match" if not ranked else "all candidates restricted"
                print(f"[{i}/{len(targets)}] {bid} {title}: {why}")
        time.sleep(0.4)

    BOOKS_JSON.write_text(
        json.dumps(books, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nDONE. downloaded/have={found}  placeholders_skipped={skipped}  no_match/failed={failed}")


JAIN_KEYWORDS = (
    "jain", "jaina", "digambar", "digambara", "shwetambar", "svetambar",
    "tirthankar", "tirthankara", "mahavir", "mahavira", "parshva", "parsva",
    "rishabh", "adinath", "samaya", "samayasara", "tattvartha", "jinendra",
    "jinvani", "jinavani", "syadvad", "syadvada", "anekant", "namokar",
    "navkar", "namokara", "prakrit", "agam", "agama", "kundakunda", "umasvati",
    "pujyapada", "samantabhadra", "gommatasara", "dravyasamgraha", "shravak",
    "shravakachar", "muni", "acharya", "aryika", "siddhant", "siddhanta",
    "kashaya", "karma", "anuyoga", "purana", "charitra", "stotra", "bhakti",
    "moksha", "ahimsa", "shatkhandagama", "dhavala", "varni", "sagar",
)


def _is_jain(doc: dict) -> bool:
    blob = " ".join([
        as_text(doc.get("title")), as_text(doc.get("creator")),
        as_text(doc.get("identifier")),
    ]).lower()
    return any(k in blob for k in JAIN_KEYWORDS)


def _detect_anuyoga(text: str) -> str:
    t = text.lower()
    pairs = [
        ("charananuyog", ("achar", "shravak", "vrat", "conduct", "ethic", "samiti", "ahimsa")),
        ("prathamanuyoga", ("purana", "charitra", "charit", "katha", "story", "tirthankar", "life")),
        ("karnanuyoga", ("trilok", "jambudvip", "jambudwip", "cosmolog", "bhugol", "khagol", "loka", "stotra", "puja")),
        ("dravyanuyog", ("tattva", "dravya", "samaya", "nyaya", "pramana", "karma", "anekant", "syadvad", "atma", "jiva")),
    ]
    for anuyoga, kws in pairs:
        if any(k in t for k in kws):
            return anuyoga
    return "all_texts"


# Broad rotation of queries to maximize unique Digambar/Jain texts on archive.org.
HARVEST_QUERIES = [
    'subject:(Jainism OR Jaina OR "Jain dharma" OR Digambara OR Jainology)',
    'subject:("Jain philosophy" OR "Jaina philosophy" OR "Jain literature" OR Prakrit)',
    '(Digambar Jain)', '(Digambara Jain)', '(Jain Granth)', '(Jain shastra)',
    '(Jain agama OR Jaina agama)', '(Jain stotra OR Jain puja OR Jain bhakti)',
    '(Jain purana OR Jain charitra)', '(Jain tirthankar OR Mahavira teachings)',
    '(Kundakunda OR Samayasara OR Pravachanasara OR Niyamasara)',
    '(Tattvartha OR Sarvarthasiddhi OR Umasvati OR Pujyapada)',
    '(Gommatasara OR Dhavala OR Shatkhandagama OR Kashayapahuda)',
    '(Akalanka OR Vidyananda OR Samantabhadra OR Aptamimansa)',
    '(Jain shravakachar OR Jain achar OR Jain niti)',
    '(Jain dharm hindi OR जैन धर्म)', '(जैन दर्शन OR जैन सिद्धांत)',
    '(जैन शास्त्र OR जैन ग्रंथ)', '(जैन पुराण OR जैन चरित्र)',
    '(Acharya Vidyasagar OR Acharya Vidyananda)',
    '(Aryika Gyanmati OR Ganini Gyanmati)',
    '(Jain karma siddhant OR Jain moksha)',
    '(Jain anekant OR syadvad OR naya)',
    '(Jaina manuscript OR Jain bhandar)',
    '(Jain cosmology OR Jain jyotish OR Jambudvipa)',
    '(Jainendra OR Jinvani OR Jinasena OR Gunabhadra)',
    'subject:(Prakrit literature OR "Ardhamagadhi")',
    '(Jain svetambar agama OR Jain sutra)',
    '(Jain ramayana OR Jain mahabharata OR Padmapurana)',
    '(Mulachara OR Bhagavati Aradhana OR Ratnakaranda)',
    '(Jain yoga OR Jain dhyan OR Jain sadhana)',
    '(Bhaktamar OR Jinasahasranama OR Jain pooja path)',
    '(Jain itihaas OR Jain sanskriti OR Jain kala)',
    '(Jain bal OR Jain kahani OR Jain katha)',
]


def scrape_iter(query: str):
    """Yield docs for a query using archive.org's cursor-based scrape API.
    Handles deep pagination and transient 5xx with backoff."""
    cursor = None
    while True:
        params = {
            "q": f"({query}) AND mediatype:texts",
            "fields": "identifier,title,creator,language,year",
            "count": 500,
        }
        if cursor:
            params["cursor"] = cursor
        data = None
        for attempt in range(6):
            try:
                r = SESSION.get(SCRAPE_URL, params=params, timeout=60)
                if r.status_code in (502, 503, 504):
                    raise RuntimeError(f"{r.status_code} backend")
                r.raise_for_status()
                data = r.json()
                break
            except Exception as exc:
                wait = min(30, 4 * (attempt + 1))
                print(f"    scrape retry {attempt+1} ({exc}); wait {wait}s")
                time.sleep(wait)
        if data is None:
            print("    scrape giving up on query")
            return
        for it in data.get("items", []):
            yield it
        cursor = data.get("cursor")
        if not cursor:
            return


def harvest(target: int, queries: list[str], prefer: str) -> None:
    """Bulk-download genuine Jain texts from archive.org collections and append
    them as new catalog entries (id: harvest-NNNN). Rotates through many queries,
    dedupes by identifier, resumable across runs."""
    BOOKS_DIR.mkdir(exist_ok=True)
    books = json.loads(BOOKS_JSON.read_text(encoding="utf-8"))

    used_ids = {
        b["source_url"].rstrip("/").split("/")[-1]
        for b in books if str(b.get("source_url", "")).startswith("https://archive.org/details/")
    }
    existing_h = [int(b["id"].split("-")[1]) for b in books if b["id"].startswith("harvest-")]
    next_n = (max(existing_h) + 1) if existing_h else 1

    print(f"Harvesting up to {target} Jain texts across {len(queries)} queries\n")
    got = 0

    def persist():
        BOOKS_JSON.write_text(json.dumps(books, ensure_ascii=False, indent=2), encoding="utf-8")

    for qi, query in enumerate(queries, 1):
        if got >= target:
            break
        print(f"-- query {qi}/{len(queries)}: {query}")
        for doc in scrape_iter(query):
            if got >= target:
                break
            ident = doc.get("identifier")
            if not ident or ident in used_ids:
                continue
            used_ids.add(ident)
            if not _is_jain(doc):
                continue
            picked = pick_file(ident, prefer)
            if not picked:
                continue
            filename, ext = picked
            bid = f"harvest-{next_n:04d}"
            dest = BOOKS_DIR / f"{bid}{ext}"
            if download(ident, filename, dest):
                title = as_text(doc.get("title")) or ident
                author = as_text(doc.get("creator")) or "Unknown"
                lang = as_text(doc.get("language")) or "unknown"
                books.append({
                    "id": bid,
                    "title": title[:200],
                    "title_hindi": "",
                    "author": author[:200],
                    "author_slug": "harvested",
                    "anuyoga": _detect_anuyoga(title),
                    "language": lang.lower()[:30],
                    "century": as_text(doc.get("year")),
                    "source_type": "scripture",
                    "source_url": f"https://archive.org/details/{ident}",
                    "file_path": f"backend/books/{dest.name}",
                    "total_chunks": 0,
                    "description": "Harvested Jain text from the Internet Archive.",
                })
                next_n += 1
                got += 1
                print(f"  [{got}/{target}] {bid} {title[:68]}")
                if got % 25 == 0:
                    persist()
            time.sleep(0.1)

    persist()
    print(f"\nHARVEST DONE. {got} new Jain texts added this run.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Download corpus books from archive.org")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", type=str, default=None, help="only ids with this prefix")
    ap.add_argument("--min-score", type=float, default=2.0)
    ap.add_argument("--prefer", choices=["text", "pdf"], default="text")
    ap.add_argument("--harvest", type=int, default=0, help="bulk-harvest N Jain texts")
    ap.add_argument("--harvest-query", type=str, default=None,
                    help="custom query (default: rotate built-in Jain query set)")
    args = ap.parse_args()
    try:
        if args.harvest:
            qs = [args.harvest_query] if args.harvest_query else HARVEST_QUERIES
            harvest(args.harvest, qs, args.prefer)
        else:
            run(args.limit, args.only, args.min_score, args.prefer)
    except KeyboardInterrupt:
        sys.exit("\ninterrupted")
