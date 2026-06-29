from __future__ import annotations

import re
from dataclasses import dataclass, field

COURSE_RE = re.compile(r"\b([A-Z]{2,5})\s?(\d{3})\b")
TERM_RE = re.compile(r"\b(Fall|Winter|Spring|Summer)\s+Term\s+\d{4}\b")
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")

@dataclass
class CitationAudit:
    ok: bool
    violations: list[str] = field(default_factory=list)

def _course_facts(snapshot: dict, course: str) -> dict | None:
    return snapshot.get("courses", {}).get(course)

def _course_times(c: dict) -> set[str]:
    out: set[str] = set()
    for s in c.get("sections", []):
        for m in s.get("meetings", []):
            if m.get("time_start"):
                out.add(m["time_start"])
            if m.get("time_end"):
                out.add(m["time_end"])
    return out

def audit_offering_answer(answer: str, snapshot: dict,
                          courses_hint: list[str] | None = None) -> CitationAudit:
    violations: list[str] = []

    mentioned = list(courses_hint or [])
    for subj, num in COURSE_RE.findall(answer):
        mentioned.append(f"{subj} {num}")
    mentioned = [c for c in dict.fromkeys(mentioned) if _course_facts(snapshot, c)]
    if not mentioned:
        return CitationAudit(ok=True)

    terms_in_answer = {m.group(0) for m in TERM_RE.finditer(answer)}
    times_in_answer = {f"{h}:{mm}" for h, mm in TIME_RE.findall(answer)}

    valid_terms: set[str] = set()
    valid_times: set[str] = set()
    for course in mentioned:
        c = _course_facts(snapshot, course)
        valid_terms |= set(c.get("terms") or [])
        valid_times |= {_norm_time(t) for t in _course_times(c)}

    for t in terms_in_answer:
        if t not in valid_terms:
            violations.append(f"answer cites term '{t}' not offered for {mentioned} in snapshot")
    for t in times_in_answer:
        if _norm_time(t) not in valid_times:
            violations.append(f"answer cites time '{t}' not in snapshot section times for {mentioned}")

    return CitationAudit(ok=not violations, violations=violations)

def _norm_time(t: str) -> str:
    h, m = t.split(":")
    return f"{int(h):02d}:{m}"
