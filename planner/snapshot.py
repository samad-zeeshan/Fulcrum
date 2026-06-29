from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_SEASON_RANK = {"Winter": 0, "Spring": 1, "Summer": 2, "Fall": 3}

def parse_term(term: str) -> tuple[int, int, str]:
    m = re.match(r"^(Fall|Winter|Spring|Summer)\s+Term\s+(\d{4})", term.strip())
    if not m:
        return (9999, 9, term.strip())
    season, year = m.group(1), int(m.group(2))
    return (year, _SEASON_RANK.get(season, 9), season)

def season_of(term: str) -> str:
    for s in ("Fall", "Winter", "Spring", "Summer"):
        if s in term:
            return s
    return term.strip()

@dataclass(frozen=True)
class CourseFacts:
    course_id: str
    units: float
    subject: str | None
    level: int | None
    terms: tuple[str, ...]
    seasons: frozenset[str]

class Snapshot:
    def __init__(self, data: dict):
        self.date: str = data.get("snapshot_date", "")
        self.source: str = data.get("source", "")
        self.term_order: list[str] = list(data.get("term_order", []))
        self.term_index: dict[str, int] = {t: i for i, t in enumerate(self.term_order)}
        self.courses: dict[str, CourseFacts] = {}
        for cid, c in data.get("courses", {}).items():
            terms = tuple(c.get("terms") or [])
            self.courses[cid] = CourseFacts(
                course_id=cid,
                units=float(c["units"]) if c.get("units") is not None else 0.0,
                subject=c.get("subject"),
                level=c.get("level"),
                terms=terms,
                seasons=frozenset(season_of(t) for t in terms),
            )

    @classmethod
    def load(cls, path: str | Path) -> "Snapshot":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def units_of(self, course: str) -> float:
        c = self.courses.get(course)
        return c.units if c else 0.0

    def level_of(self, course: str) -> int | None:
        c = self.courses.get(course)
        return c.level if c else None

    def is_offered_in_term(self, course: str, term: str) -> bool:
        c = self.courses.get(course)
        return bool(c and term in c.terms)

    def is_offered_in_season(self, course: str, season: str) -> bool:
        c = self.courses.get(course)
        return bool(c and season in c.seasons)

    def matches_pattern(self, course: str, pattern: dict) -> bool:
        c = self.courses.get(course)
        if c is None:
            return False
        if "subject" in pattern and c.subject != pattern["subject"]:
            return False
        if c.level is None:
            return False
        if "level_in" in pattern and c.level not in pattern["level_in"]:
            return False
        if "level_gte" in pattern and c.level < pattern["level_gte"]:
            return False
        return True

    def courses_matching(self, pattern: dict) -> set[str]:
        return {cid for cid in self.courses if self.matches_pattern(cid, pattern)}
