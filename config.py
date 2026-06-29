from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
RAW = CORPUS / "raw"
RAW_COURSE = RAW / "course"
RAW_SUBJECT = RAW / "subject"
RAW_PROGRAM = RAW / "program"
RAW_INDEX = RAW / "index"
MANIFEST = RAW / "_manifest.jsonl"

COURSES_OUT = CORPUS / "courses.jsonl"
PROGRAMS_OUT = CORPUS / "programs.jsonl"
RUN_REPORT = CORPUS / "RUN_REPORT.md"

USER_AGENT = os.environ.get(
    "UA_SCRAPER_UA",
    "UAlbertaCatalogueScraper/1.0 (+research; contact: samad.z33shan@gmail.com)",
)

APPS_DELAY = float(os.environ.get("UA_APPS_DELAY", "0.7"))

CAL_DELAY = float(os.environ.get("UA_CAL_DELAY", "120"))

MAX_RETRIES = 5
BACKOFF_BASE = 1.5
BACKOFF_CAP = 60.0
REQUEST_TIMEOUT = 30.0

APPS_BASE = "https://apps.ualberta.ca"
COURSE_INDEX_URL = f"{APPS_BASE}/catalogue/course"

APPS_ROBOTS_DISALLOW = ("/catalogue/archive", "/catalogue/syllabus", "/ezsend", "/saml2")

CAL_BASE = "https://calendar.ualberta.ca"
CATOID = "69"

PROGRAM_URL_TMPL = f"{CAL_BASE}/preview_program.php?catoid={{catoid}}&poid={{poid}}"

UNDERGRAD_PROGRAMS_NAVOID = "20886"
GRAD_PROGRAMS_NAVOID = "20894"
CONTENT_URL_TMPL = f"{CAL_BASE}/content.php?catoid={{catoid}}&navoid={{navoid}}"

CAL_ROBOTS_DISALLOW = ("/portfolio.php", "/portfolio_nopop.php", "/ajax/", "/search_advanced.php")

GOLD_POIDS = {
    "110935": "Bachelor of Science Computing Science Subject Area (Science)",

    "109967": "Bachelor of Arts (Arts)",
    "110573": "Bachelor of Science in Nursing - Collaborative (Nursing)",
}

SEASON_OFFSET = {"Winter": 0, "Spring": 1, "Summer": 2, "Fall": 3}
_ANCHOR_CODE = 1940
_ANCHOR_YEAR = 2026

def term_code(season: str, year: int) -> str | None:
    off = SEASON_OFFSET.get(season)
    if off is None:
        return None
    return str(_ANCHOR_CODE + (year - _ANCHOR_YEAR) * 40 + off * 10)

def term_code_from_label(label: str) -> str | None:
    import re

    m = re.match(r"\s*(Winter|Spring|Summer|Fall)\s+Term\s+(\d{4})", label)
    if not m:
        return None
    return term_code(m.group(1), int(m.group(2)))
