"""Rebuild data/books.json after it was truncated, using:
  1. build_catalog.build()  -> the deterministic 600-entry base catalog
  2. the 1,050 downloaded files on disk in backend/books/
  3. harvest logs (logs/*.log) for harvest-NNNN -> title mapping

Canonical/acharya entries get their file_path re-attached by id; every
harvest-NNNN file becomes a fresh catalog entry with best-effort metadata.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
BOOKS_DIR = BASE / "books"
BOOKS_JSON = ROOT / "data" / "books.json"
LOGS = ROOT / "logs"

sys.path.insert(0, str(ROOT / "data"))
from build_catalog import build as build_base  # noqa: E402


def detect_anuyoga(text: str) -> str:
    t = text.lower()
    pairs = [
        ("charananuyog", ("achar", "shravak", "vrat", "conduct", "ethic", "ahimsa", "niti")),
        ("prathamanuyoga", ("purana", "charitra", "charit", "katha", "story", "tirthankar", "ramayan", "life", "biograph")),
        ("karnanuyoga", ("trilok", "jambudvip", "jambudwip", "cosmolog", "bhugol", "khagol", "stotra", "puja", "astronom", "geograph")),
        ("dravyanuyog", ("tattva", "dravya", "samaya", "nyaya", "pramana", "karma", "anekant", "syadvad", "atma", "jiva", "philosoph", "logic")),
    ]
    for anuyoga, kws in pairs:
        if any(k in t for k in kws):
            return anuyoga
    return "all_texts"


def load_harvest_titles() -> dict[str, str]:
    """Map harvest-NNNN -> title from any logs/*.log line like
    '  [12/300] harvest-0012 Some Title'."""
    titles: dict[str, str] = {}
    pat = re.compile(r"(harvest-\d{4})\s+(.+?)\s*$")
    line_pat = re.compile(r"\[\d+/\d+\]\s+(harvest-\d{4})\s+(.*)")
    for log in LOGS.glob("*.log"):
        try:
            raw = log.read_bytes()
            # PowerShell Tee-Object often writes UTF-16; sniff and decode.
            if b"\x00" in raw[:200]:
                text = raw.decode("utf-16", errors="ignore")
            else:
                text = raw.decode("utf-8", errors="ignore")
            for line in text.splitlines():
                m = line_pat.search(line)
                if not m:
                    continue
                hid, title = m.group(1), m.group(2).strip()
                # Prefer the first (longest) non-truncated title we see.
                if title and (hid not in titles or len(title) > len(titles[hid])):
                    titles[hid] = title
        except Exception:
            continue
    return titles


def first_text_line(path: Path, limit: int = 4000) -> str:
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except Exception:
        return ""
    for ln in head.splitlines():
        ln = ln.strip()
        if len(ln) > 8:
            return ln[:120]
    return ""


def main() -> None:
    base = build_base()  # 600 entries, file_path=""
    by_id = {b["id"]: b for b in base}

    disk = {p.stem: p for p in BOOKS_DIR.iterdir() if p.is_file() and p.suffix in (".txt", ".pdf")}
    print(f"files on disk: {len(disk)}")

    attached = 0
    for stem, path in disk.items():
        if stem in by_id:
            by_id[stem]["file_path"] = f"backend/books/{path.name}"
            by_id[stem]["source_type"] = by_id[stem].get("source_type", "scripture")
            attached += 1

    titles = load_harvest_titles()
    print(f"harvest titles recovered from logs: {len(titles)}")

    harvested = 0
    for stem, path in sorted(disk.items()):
        if not stem.startswith("harvest-"):
            continue
        title = titles.get(stem) or first_text_line(path) or f"Jain Text {stem}"
        anuyoga = detect_anuyoga(title + " " + first_text_line(path))
        base.append({
            "id": stem,
            "title": title[:200],
            "title_hindi": "",
            "author": "Harvested (Internet Archive)",
            "author_slug": "harvested",
            "anuyoga": anuyoga,
            "language": "unknown",
            "century": "",
            "source_type": "scripture",
            "source_url": "https://archive.org/",
            "file_path": f"backend/books/{path.name}",
            "total_chunks": 0,
            "description": "Harvested Digambar/Jain text from the Internet Archive.",
        })
        harvested += 1

    BOOKS_JSON.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    total_files = sum(1 for b in base if b.get("file_path"))
    print(f"catalog rebuilt: {len(base)} entries | base file_path attached: {attached} "
          f"| harvested entries: {harvested} | total with file_path: {total_files}")
    print(f"written -> {BOOKS_JSON}")


if __name__ == "__main__":
    main()
