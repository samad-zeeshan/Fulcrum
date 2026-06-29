from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from planner import Gold, Plan, Snapshot, solve, validate
from planner.expr import referenced_courses

REPO = Path(__file__).resolve().parents[2]

@dataclass
class QueryGold:
    qid: str
    qtype: str
    data: dict = field(default_factory=dict)

def compute_gold(query: dict, gold: Gold, snap: Snapshot,
                 cfg=None) -> QueryGold:
    t = query["type"]
    if t == "factual_offered":
        offered = snap.is_offered_in_term(query["course"], query["term"])
        return QueryGold(query["id"], t, {"offered": offered,
                                          "course": query["course"], "term": query["term"]})
    if t == "factual_prereq":
        entry = gold.prerequisites.get(query["course"])
        courses = referenced_courses(entry.prereq) if entry else set()
        return QueryGold(query["id"], t, {"prereq_courses": sorted(courses),
                                          "source": entry.source if entry else None})
    if t == "plan_validity":
        plan = Plan.load(REPO / query["plan_ref"])
        res = validate(plan, gold, snap, cfg) if cfg else validate(plan, gold, snap)
        return QueryGold(query["id"], t, {"valid": res.valid,
                                          "failure_codes": sorted({f.code for f in res.failures})})
    if t == "plan_construction":
        res = solve(query.get("taken", []), gold, snap, cfg) if cfg else solve(query.get("taken", []), gold, snap)
        return QueryGold(query["id"], t, {"reference_terms": res.terms_to_graduate,
                                          "solve_found": res.found})
    raise ValueError(f"unknown query type {t}")
