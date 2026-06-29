"""
Loads the gold answer key: program rules, conditionals, exclusions and prereqs.

This is the source of truth the eval grades against and the engine validates with.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = REPO / "eval" / "gold" / "cs_major.gold.yaml"

@dataclass
class Group:
    id: str
    type: str
    members: list = field(default_factory=list)
    options: list[str] = field(default_factory=list)
    units_required: float = 0.0
    pattern: dict | None = None

@dataclass
class Conditional:
    id: str
    when: dict
    effects: list[dict]

@dataclass
class CreditExclusion:
    courses: list[str]
    source: str | None

@dataclass
class PrereqEntry:
    course: str
    prereq: object | None
    coreq: object | None
    source: str | None
    coreq_source: str | None
    confidence: str | None
    bridge: bool = False

@dataclass
class Gold:
    program: dict
    conventions: dict
    courses: dict[str, dict]
    groups: list[Group]
    conditionals: list[Conditional]
    credit_exclusions: list[CreditExclusion]
    prerequisites: dict[str, PrereqEntry]
    raw: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_GOLD) -> "Gold":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

        groups = [
            Group(
                id=g["id"],
                type=g["type"],
                members=g.get("members", []) or [],
                options=g.get("options", []) or [],
                units_required=float(g.get("units_required", 0) or 0),
                pattern=g.get("pattern"),
            )
            for g in data.get("groups", [])
        ]

        conditionals = [
            Conditional(id=c["id"], when=c.get("when", {}), effects=c.get("effects", []))
            for c in data.get("conditionals", [])
        ]

        exclusions = [
            CreditExclusion(courses=list(x["set"]), source=x.get("source"))
            for x in data.get("credit_exclusions", [])
        ]

        prereqs: dict[str, PrereqEntry] = {}
        for course, entry in (data.get("prerequisites") or {}).items():
            entry = entry or {}
            prereqs[course] = PrereqEntry(
                course=course,
                prereq=entry.get("prereq"),
                coreq=entry.get("coreq"),
                source=entry.get("source"),
                coreq_source=entry.get("coreq_source"),
                confidence=entry.get("confidence"),
                bridge=bool(entry.get("bridge", False)),
            )

        return cls(
            program=data.get("program", {}),
            conventions=data.get("conventions", {}),
            courses=data.get("courses", {}) or {},
            groups=groups,
            conditionals=conditionals,
            credit_exclusions=exclusions,
            prerequisites=prereqs,
            raw=data,
        )

    def named_courses(self) -> set[str]:
        return set(self.courses.keys())

    def bridge_courses(self) -> set[str]:
        return {c for c, e in self.prerequisites.items() if e.bridge}

    # The course set graded plans may draw from: named core plus bridge electives.
    def eval_scope(self) -> set[str]:
        return self.named_courses() | self.bridge_courses()

    def group(self, gid: str) -> Group:
        for g in self.groups:
            if g.id == gid:
                return g
        raise KeyError(gid)
