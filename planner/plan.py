from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

@dataclass
class PlanTerm:
    term: str
    courses: list[str]

@dataclass
class Plan:
    plan_id: str
    terms: list[PlanTerm]
    taken: list[str] = field(default_factory=list)
    description: str = ""

    expected: str | None = None
    expected_reasons: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Plan":
        terms = [PlanTerm(term=t["term"], courses=list(t.get("courses", []) or []))
                 for t in data.get("terms", [])]
        return cls(
            plan_id=data.get("plan_id", "<unnamed>"),
            terms=terms,
            taken=list(data.get("taken", []) or []),
            description=data.get("description", ""),
            expected=data.get("expected"),
            expected_reasons=list(data.get("expected_reasons", []) or []),
        )

    @classmethod
    def load(cls, path: str | Path) -> "Plan":
        return cls.from_dict(yaml.safe_load(Path(path).read_text(encoding="utf-8")))

    def all_courses(self) -> list[str]:
        out = list(self.taken)
        for t in self.terms:
            out.extend(t.courses)
        return out

    def scheduled_courses(self) -> list[str]:
        return [c for t in self.terms for c in t.courses]

    def term_of(self, course: str) -> int | None:
        if course in self.taken:
            return -1
        for i, t in enumerate(self.terms):
            if course in t.courses:
                return i
        return None
