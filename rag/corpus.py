"""
Builds retrieval spans from a snapshot.

One span per course plus one per (course, term) offering, each carrying the
facts a citation audit can later check against.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

def load_snapshot(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

@dataclass
class Span:
    id: str
    kind: str
    course: str
    text: str
    term: str | None = None
    facts: dict = field(default_factory=dict)
    embed_text: str | None = None

    def __post_init__(self):
        if self.embed_text is None:
            # Repeat the course code so the lexical retriever weights it; exact
            # codes matter more than the surrounding prose on this corpus.
            self.embed_text = f"{self.course} {self.course} {self.text}"

def _fmt_meeting(m: dict) -> str:
    days = "".join(m.get("days") or [])
    ts, te = m.get("time_start"), m.get("time_end")
    when = f"{days} {ts}-{te}" if ts else (f"{days} (time TBA)" if days else "time TBA")
    return when.strip()

def build_spans(snapshot: dict, subjects: set[str] | None = None) -> list[Span]:
    spans: list[Span] = []
    for cid, c in sorted(snapshot.get("courses", {}).items()):
        if subjects and c.get("subject") not in subjects:
            continue
        terms_list = c.get("terms") or []
        terms = ", ".join(terms_list) if terms_list else "not offered in this snapshot"
        title = c.get("title")
        units = c.get("units") or 0
        prereq = c.get("prereq_raw") or "none listed"
        course_text = (
            f"[{cid}] {title or cid} ({units:g} units, {c.get('level')}-level). "
            f"Offered: {terms}. Prerequisite: {prereq}."
        )
        spans.append(Span(id=f"{cid}::course", kind="course", course=cid, text=course_text,
                          facts={"terms": list(terms_list), "units": units,
                                 "level": c.get("level"), "title": title,
                                 "prereq_raw": c.get("prereq_raw")}))

        # A separate span per term so an offering question retrieves the right term.
        by_term: dict[str, list[dict]] = {}
        for s in c.get("sections", []):
            by_term.setdefault(s.get("term"), []).append(s)
        for term, secs in by_term.items():
            parts, times, total_cap = [], [], 0
            for s in secs:
                when = "; ".join(_fmt_meeting(m) for m in s.get("meetings", [])) or "time TBA"
                cap = s.get("capacity")
                if cap is not None:
                    total_cap += cap
                parts.append(f"{s.get('component')} {s.get('section')} {when}"
                             + (f" (capacity {cap})" if cap is not None else ""))
                times += [(m.get("time_start"), m.get("time_end"))
                          for m in s.get("meetings", []) if m.get("time_start")]
            off_id = f"{cid}::{term}"
            off_text = (f"[{off_id}] {cid} in {term}: " + "; ".join(parts)
                        + f". Total capacity {total_cap}.")
            spans.append(Span(id=off_id, kind="offering", course=cid, term=term, text=off_text,
                              facts={"term": term, "sections": len(secs),
                                     "total_capacity": total_cap, "times": times}))
    return spans
