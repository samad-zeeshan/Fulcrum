"""
Offline pass: turns the cached raw HTML into structured JSONL and a run report.

Deterministic and network-free; reads only what fetch.py left in corpus/raw.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import config
import parsers
import util

# Union of what the manifest recorded and whatever HTML is actually on disk, so
# a parse still works if the manifest is incomplete.
def _course_files(manifest: dict[str, dict]) -> list[dict]:
    out: dict[str, dict] = {}
    for url, rec in manifest.items():
        if rec.get("kind") == "course" and rec.get("ok"):
            p = config.ROOT / rec["path"]
            if p.exists():
                out[str(p)] = {"path": p, "url": url, "fetched_at": rec.get("fetched_at")}

    for p in config.RAW_COURSE.glob("*.html"):
        if str(p) not in out:
            subj, _, num = p.stem.partition("__")
            out[str(p)] = {
                "path": p,
                "url": f"{config.COURSE_INDEX_URL}/{subj}/{num}",
                "fetched_at": None,
            }
    return [out[k] for k in sorted(out)]

def _program_files(manifest: dict[str, dict]) -> list[dict]:
    out: dict[str, dict] = {}
    for url, rec in manifest.items():
        if rec.get("kind") == "program" and rec.get("ok"):
            p = config.ROOT / rec["path"]
            if p.exists():
                out[str(p)] = {
                    "path": p,
                    "url": url,
                    "poid": rec.get("poid"),
                    "tier": rec.get("tier", "silver"),
                    "fetched_at": rec.get("fetched_at"),
                }
    for p in config.RAW_PROGRAM.glob("*.html"):
        if str(p) not in out:
            poid = p.stem
            out[str(p)] = {
                "path": p,
                "url": config.PROGRAM_URL_TMPL.format(catoid=config.CATOID, poid=poid),
                "poid": poid,
                "tier": "gold" if poid in config.GOLD_POIDS else "silver",
                "fetched_at": None,
            }
    return [out[k] for k in sorted(out)]

# Parse every cached course. Odd shapes are pushed to failure_queue for human
# review rather than raised, so one bad page never stops the run.
def parse_all_courses(manifest: dict[str, dict], failure_queue: list[dict]) -> list[dict]:
    records: list[dict] = []
    for item in _course_files(manifest):
        html = util.read_html(item["path"])
        course, flags = parsers.parse_course(html, item["url"], item["fetched_at"])
        records.append(course.as_dict())
        for fl in flags:
            failure_queue.append({"scope": "course", "id": course.course_id, "detail": fl})
    records.sort(key=lambda r: (r["subject"], _num_key(r["catalog_number"]), r["course_id"]))
    return records

def parse_all_programs(manifest: dict[str, dict], failure_queue: list[dict]) -> list[dict]:
    records: list[dict] = []
    for item in _program_files(manifest):
        html = util.read_html(item["path"])
        program, flags, dumps = parsers.parse_program(
            html, item["poid"], config.CATOID, item["tier"], item["url"], item["fetched_at"]
        )
        records.append(program.as_dict())
        for fl in flags:
            failure_queue.append({"scope": "program", "id": item["poid"], "detail": fl})

        for idx, raw_html in dumps:
            dump_path = config.RAW_PROGRAM / f"{item['poid']}_block_{idx}.html"
            util.write_text(dump_path, raw_html)
            failure_queue.append(
                {
                    "scope": "program",
                    "id": item["poid"],
                    "detail": f"raw block dumped -> {dump_path.relative_to(config.ROOT)}",
                }
            )
    records.sort(key=lambda r: int(r["poid"]) if r["poid"].isdigit() else 0)
    return records

def _num_key(num: str) -> tuple[int, str]:
    import re

    m = re.match(r"(\d+)([A-Za-z]*)", num or "")
    return (int(m.group(1)), m.group(2)) if m else (0, num or "")

def build_report(
    courses: list[dict],
    programs: list[dict],
    failure_queue: list[dict],
    args: argparse.Namespace,
) -> str:
    n_sections = sum(len(c["sections"]) for c in courses)
    n_subjects = len({c["subject"] for c in courses})
    ugrd = sum(1 for c in courses if c.get("career") == "UGRD")
    grad = sum(1 for c in courses if c.get("career") and c["career"] != "UGRD")

    # Cross-check parsed section counts against the ua__cat_sections meta hint;
    # a mismatch usually means the section table parser missed something.
    mismatches = []
    for c in courses:
        meta = c.get("meta_sections")
        if meta is not None and len(c["sections"]) != meta:
            mismatches.append((c["course_id"], len(c["sections"]), meta))

    gold = [p for p in programs if p["tier"] == "gold"]
    silver = [p for p in programs if p["tier"] == "silver"]
    needs_review = [p for p in programs if p["parse_confidence"] == "needs_review"]

    L: list[str] = []
    L.append("# RUN REPORT -- University of Alberta Catalogue Scraper")
    L.append("")
    L.append(f"_Generated: {util.now_iso()}_")
    L.append("")

    L.append("## 1. Phase 0 -- structured-endpoint probe & configuration")
    L.append("")
    L.append(
        "- **No clean public JSON/structured course API was found.** Course pages on "
        "`apps.ualberta.ca` are server-rendered HTML and expose machine-readable "
        "`<meta name=\"ua__cat_*\">` tags in `<head>` (course id, subject, catalog, "
        "title, credits, faculty, career, terms, section counts). The scraper reads "
        "those meta tags as the primary structured source and parses the section "
        "tables from the page body. No headless browser is needed for Module A."
    )
    L.append(
        "- **Module B (programs) requires a headless browser.** `calendar.ualberta.ca` "
        "program pages (Acalog `preview_program.php`) sit behind an AWS-WAF JavaScript "
        "challenge (`x-amzn-waf-action: challenge`, HTTP 202). A plain HTTP client only "
        "receives the JS interstitial, so Module B fetches through Playwright/Chromium, "
        "which solves the challenge and returns the rendered HTML."
    )
    L.append(
        "- **robots.txt is respected.** `apps.ualberta.ca` disallows `/catalogue/archive` "
        "for `*` -- so the historical-term archive scheme is **not** crawled; the live "
        "course page already lists every currently scheduled term. "
        "`calendar.ualberta.ca` declares `crawl-delay: 120` for `*`, honoured by default "
        f"(CAL_DELAY={config.CAL_DELAY:g}s; APPS_DELAY={config.APPS_DELAY:g}s)."
    )
    L.append("")
    L.append("### Config used")
    L.append("")
    L.append(f"- module: `{args.module}`  |  program mode: `{args.mode}`  |  term filter: `{args.term}`")
    L.append(f"- catoid: `{config.CATOID}`  |  gold poids: `{', '.join(config.GOLD_POIDS)}`")
    L.append(f"- user-agent: `{config.USER_AGENT}`")
    L.append("")

    L.append("## 2. Counts")
    L.append("")
    L.append(f"- Subjects represented in parsed courses: **{n_subjects}**")
    L.append(f"- Courses parsed: **{len(courses)}**  (UGRD: {ugrd}, non-UGRD: {grad})")
    L.append(f"- Sections parsed: **{n_sections}**")
    L.append(f"- Programs parsed: **{len(programs)}**  (gold: {len(gold)}, silver: {len(silver)})")
    L.append(f"- Programs flagged `needs_review`: **{len(needs_review)}**")
    L.append("")
    L.append("### Section-count cross-check (parsed vs `ua__cat_sections` meta)")
    L.append("")
    if not mismatches:
        L.append("- No mismatches: every course's parsed section count equals its meta hint. ✅")
    else:
        L.append(f"- {len(mismatches)} course(s) where parsed count != meta hint:")
        for cid, got, meta in mismatches[:200]:
            L.append(f"  - `{cid}`: parsed={got}, meta={meta}")
    L.append("")

    L.append("## 3. Samples")
    L.append("")
    L.append("### Sample course records (up to 3, with sections)")
    L.append("")
    for c in _pick_samples(courses):
        L.append("```json")
        L.append(json.dumps(c, indent=2, ensure_ascii=False))
        L.append("```")
        L.append("")
    L.append("### Sample program record (1)")
    L.append("")
    sample_prog = (gold or programs)[:1]
    for p in sample_prog:
        L.append("```json")
        L.append(json.dumps(p, indent=2, ensure_ascii=False))
        L.append("```")
        L.append("")

    L.append("## 4. Parse-failure queue (human gold-verification input)")
    L.append("")
    L.append(
        "Every record below hit an unexpected shape during extraction. This is the "
        "complete, specific list for manual review -- not a sample."
    )
    L.append("")
    if not failure_queue:
        L.append("- (empty) -- no anomalies encountered.")
    else:
        by_scope: dict[str, list[dict]] = {}
        for f in failure_queue:
            by_scope.setdefault(f["scope"], []).append(f)
        for scope in sorted(by_scope):
            items = by_scope[scope]
            L.append(f"### {scope} ({len(items)})")
            L.append("")
            for f in items:
                L.append(f"- `{f['id']}` — {f['detail']}")
            L.append("")

    L.append("## 5. Coverage (silver tier only)")
    L.append("")
    if silver:
        L.append(f"- Silver programs parsed: **{len(silver)}**.")
        L.append(
            "- Silver is best-effort breadth and is **never graded**. No accuracy claims "
            "are made anywhere in this output -- the scraper produces facts, not answers."
        )
    else:
        L.append("- No silver-tier programs in this run (gold mode).")
    L.append("")
    return "\n".join(L)

# Prefer courses that actually have sections, with CMPUT 174 first as a stable
# sample for the report.
def _pick_samples(courses: list[dict]) -> list[dict]:
    with_sec = [c for c in courses if c["sections"]]
    pool = with_sec or courses

    pool = sorted(pool, key=lambda c: (c["course_id"] != "CMPUT 174", c["subject"], _num_key(c["catalog_number"])))
    return pool[:3]

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parse cached UAlberta HTML into structured JSONL + RUN_REPORT.")
    ap.add_argument("--module", choices=["courses", "programs", "all"], default="all")
    ap.add_argument("--mode", choices=["gold", "silver"], default="gold", help="reported program mode")
    ap.add_argument("--term", default="all", help="optional term filter for section reporting")
    args = ap.parse_args(argv)

    util.ensure_dirs()
    manifest = util.load_manifest()
    failure_queue: list[dict] = []

    courses: list[dict] = []
    programs: list[dict] = []

    if args.module in ("courses", "all"):
        courses = parse_all_courses(manifest, failure_queue)
        util.write_jsonl(config.COURSES_OUT, courses)
        print(f"[parse] wrote {len(courses)} courses -> {config.COURSES_OUT.name}")

    if args.module in ("programs", "all"):
        programs = parse_all_programs(manifest, failure_queue)
        util.write_jsonl(config.PROGRAMS_OUT, programs)
        print(f"[parse] wrote {len(programs)} programs -> {config.PROGRAMS_OUT.name}")

    report = build_report(courses, programs, failure_queue, args)
    util.write_text(config.RUN_REPORT, report)
    print(f"[parse] wrote report -> {config.RUN_REPORT.name}  ({len(failure_queue)} queue items)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
