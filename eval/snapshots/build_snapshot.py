from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = REPO / "corpus" / "courses.jsonl"

_TERM_TYPE_RE = re.compile(r"^(Fall|Winter|Spring|Summer)\b")

def term_type(term: str) -> str:
    m = _TERM_TYPE_RE.match(term.strip())
    return m.group(1) if m else term.strip()

def course_level(catalog_number: str) -> int | None:
    digits = re.match(r"(\d+)", catalog_number.strip())
    if not digits:
        return None
    return (int(digits.group(1)) // 100) * 100

def _term_sort_key(term: str) -> tuple[int, int]:
    season_rank = {"Winter": 0, "Spring": 1, "Summer": 2, "Fall": 3}
    m = re.match(r"^(Fall|Winter|Spring|Summer)\s+Term\s+(\d{4})", term.strip())
    if not m:
        return (9999, 9)
    season, year = m.group(1), int(m.group(2))
    return (year, season_rank.get(season, 9))

def _compact_section(s: dict) -> dict:
    return {
        "term": s.get("term"),
        "component": s.get("component"),
        "section": s.get("section"),
        "class_id": s.get("class_id"),
        "capacity": s.get("capacity"),
        "meetings": [
            {
                "days": m.get("days"),
                "time_start": m.get("time_start"),
                "time_end": m.get("time_end"),
                "date_start": m.get("date_start"),
                "date_end": m.get("date_end"),
            }
            for m in (s.get("meetings") or [])
        ],
    }

def build(corpus_path: Path, snapshot_date: str | None) -> dict:
    courses: dict[str, dict] = {}
    all_terms: set[str] = set()
    corpus_fetched: str | None = None

    with corpus_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cid = rec["course_id"]
            terms = list(rec.get("terms_offered") or [])
            all_terms.update(terms)
            if corpus_fetched is None:
                corpus_fetched = rec.get("fetched_at")
            courses[cid] = {
                "units": rec.get("credits"),
                "subject": rec.get("subject"),
                "level": course_level(rec.get("catalog_number", "")),
                "title": rec.get("title"),
                "terms": sorted(terms, key=_term_sort_key),
                "prereq_raw": rec.get("prereq_raw"),
                "coreq_raw": rec.get("coreq_raw"),
                "credit_exclusion_raw": rec.get("credit_exclusion_raw"),

                "sections": [_compact_section(s) for s in (rec.get("sections") or [])],
            }

    term_order = sorted(all_terms, key=_term_sort_key)
    date = snapshot_date or (corpus_fetched or "")[:10]
    return {
        "snapshot_date": date,
        "source": f"{corpus_path.as_posix()} (corpus fetched_at {corpus_fetched})",
        "term_order": term_order,
        "term_types": {t: term_type(t) for t in term_order},
        "courses": courses,
    }

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--date", default=None, help="snapshot date (default: corpus fetched_at)")
    ap.add_argument("--out", type=Path, default=None, help="output path (default: eval/snapshots/<date>/offerings.json)")
    args = ap.parse_args()

    snap = build(args.corpus, args.date)
    out = args.out or (REPO / "eval" / "snapshots" / snap["snapshot_date"] / "offerings.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}  ({len(snap['courses'])} courses, terms={snap['term_order']})")

if __name__ == "__main__":
    main()
