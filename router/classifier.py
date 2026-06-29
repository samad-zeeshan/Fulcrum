"""
Interpretable query router: keyword scores decide rag, cag or compound.

No model and no planner import, so the routing decision stays explainable and
the spine rule R2 (router never touches the engine) holds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

OFFERING_TERMS = [
    "offered", "offering", "when", "what time", "time", "times", "schedule",
    "seat", "seats", "capacity", "full", "section", "lecture time", "room",
    "next term", "this term", "fall", "winter", "spring", "summer", "available",
]

CONSTRUCTION_TERMS = [
    "build a plan", "build a course plan", "course plan", "plan that completes",
    "plan to finish", "completes the computing science major", "finish the major",
]
RULES_TERMS = [
    "prerequisite", "prereq", "require", "required", "requirement", "units",
    "credit", "exclusion", "valid", "invalid", "graduate", "eligible", "plan",
    "need to take", "can i take", "do i need", "satisfy", "count toward", "rule",
]

_WORD = re.compile(r"[a-z]+")

def _score(text: str, terms: list[str]) -> tuple[int, list[str]]:
    t = text.lower()
    hits = [kw for kw in terms if kw in t]
    return len(hits), hits

@dataclass
class RouteDecision:
    route: str
    offering_score: int
    rules_score: int
    features: dict = field(default_factory=dict)

    @property
    def explanation(self) -> str:
        return (f"route={self.route} (offering={self.offering_score} "
                f"{self.features.get('offering_hits')}, rules={self.rules_score} "
                f"{self.features.get('rules_hits')})")

def classify(query: str, compound_margin: int = 1) -> RouteDecision:
    o, ohits = _score(query, OFFERING_TERMS)
    r, rhits = _score(query, RULES_TERMS)
    chits = [kw for kw in CONSTRUCTION_TERMS if kw in query.lower()]
    feats = {"offering_hits": ohits, "rules_hits": rhits, "construction_hits": chits}

    # An explicit "build me a plan" ask always needs both paths.
    if chits:
        return RouteDecision(route="compound", offering_score=o, rules_score=r, features=feats)

    # Both sides score and are close: treat it as compound rather than guess one.
    if o > 0 and r > 0 and abs(o - r) <= compound_margin:
        route = "compound"
    elif o > r:
        route = "rag"
    elif r > o:
        route = "cag"
    else:

        route = "rag" if o == 0 else "compound"
    return RouteDecision(route=route, offering_score=o, rules_score=r, features=feats)
