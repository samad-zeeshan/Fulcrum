"""
Deterministic grader for the eval harness.

Scores each answer against the gold with no LLM in the loop, so the same answer
always gets the same grade.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

from planner import Gold, Plan, Snapshot, validate
from planner.config import EngineConfig
from planner.expr import EvalContext, evaluate

from rag.citation_audit import audit_offering_answer
from .gold import QueryGold

# Cheap keyword polarity for yes/no and valid/invalid answers.
_NEG = ("not offered", "isn't offered", "is not offered", "not available", "unavailable",
        "no longer", "not scheduled", "not being offered", "no, ", "no.", "not run")
_POS = ("is offered", "yes", "offered in", "available", "runs", "is scheduled", "is being offered")
_INVALID = ("invalid", "not valid", "isn't valid", "does not satisfy", "doesn't satisfy",
            "fails", "not complete", "incomplete", "violat")
_VALID = ("valid", "satisfies", "meets all", "is complete", "fulfills", "fulfil")
# Pulls course codes like "CMPUT 174" out of free text.
COURSE_RE = re.compile(r"\b([A-Z]{2,5})\s?(\d{3})\b")

@dataclass
class Grade:
    qid: str
    qtype: str
    quality: float
    citation_ok: bool
    detail: dict = field(default_factory=dict)

def _yesno(text: str) -> bool | None:
    t = text.lower()
    if any(k in t for k in _NEG):
        return False
    if any(k in t for k in _POS):
        return True
    return None

def _validinvalid(text: str) -> bool | None:
    t = text.lower()
    if any(k in t for k in _INVALID):
        return False
    if any(k in t for k in _VALID):
        return True
    return None

def _codes(text: str) -> set[str]:
    return {f"{s} {n}" for s, n in COURSE_RE.findall(text)}

_SEASONS = ("Fall", "Winter", "Spring", "Summer")
_CYCLE = ("Fall", "Winter")

def _has_season(label: str) -> bool:
    return any(sn in label for sn in _SEASONS)

# LLMs return loosely shaped plan YAML, so normalise it before the engine sees it.
def _sanitise_plan_data(data: dict) -> dict:
    terms = []
    for i, t in enumerate(data.get("terms") or []):
        if not isinstance(t, dict):
            continue
        label = str(t.get("term", t.get("name", "")))
        if not _has_season(label):
            label = f"{_CYCLE[i % len(_CYCLE)]} (plan term {i + 1})"
        courses = t.get("courses") or t.get("course") or []
        if isinstance(courses, str):
            courses = [courses]
        terms.append({"term": label, "courses": [str(c) for c in courses if c]})
    taken = data.get("taken") or []
    if isinstance(taken, str):
        taken = [taken]
    return {"terms": terms, "taken": [str(c) for c in taken]}

def extract_plan(text: str) -> Plan | None:
    blocks = re.findall(r"```(?:ya?ml|json)?\s*(.*?)```", text, re.S)
    candidates = blocks + [text]
    for blob in candidates:
        try:
            data = yaml.safe_load(blob)
        except Exception:
            continue
        if isinstance(data, dict) and "terms" in data:
            try:
                return Plan.from_dict(_sanitise_plan_data(data))
            except Exception:
                continue
    return None

def grade(query: dict, qg: QueryGold, answer_text: str, snapshot_dict: dict,
          gold: Gold, snap: Snapshot, cited_clauses: list[str] | None = None,
          cfg=None) -> Grade:
    t = query["type"]

    if t == "factual_offered":
        pred = _yesno(answer_text)
        quality = 1.0 if pred is not None and pred == qg.data["offered"] else 0.0
        cit = audit_offering_answer(answer_text, snapshot_dict, courses_hint=[query["course"]])
        return Grade(query["id"], t, quality, cit.ok,
                     {"pred": pred, "gold": qg.data["offered"], "violations": cit.violations})

    if t == "factual_prereq":
        ans_codes = _codes(answer_text)
        entry = gold.prerequisites.get(query["course"])
        prereq = entry.prereq if entry else None

        ctx = EvalContext(
            available=lambda c: c in ans_codes,
            is_program_course=lambda c: True,
            available_matching=lambda pat: bool(ans_codes),
            cfg=EngineConfig(enforce_external_prereqs=True, hs_satisfied_by_admission=True),
        )
        if prereq is None:
            quality = 1.0 if not ans_codes else 0.5
        else:
            # Partial credit: score the fraction of required clauses the answer
            # covers, with one_of groups handled by the expression evaluator.
            conjuncts = prereq["all_of"] if isinstance(prereq, dict) and "all_of" in prereq else [prereq]
            sat = sum(1.0 for c in conjuncts if evaluate(c, ctx))
            quality = sat / len(conjuncts)
        cit_ok = (not cited_clauses) or any(query["course"] in c for c in cited_clauses)
        return Grade(query["id"], t, quality, cit_ok,
                     {"answer_courses": sorted(ans_codes), "source": qg.data.get("source")})

    if t == "plan_validity":
        pred = _validinvalid(answer_text)
        quality = 1.0 if pred is not None and pred == qg.data["valid"] else 0.0
        return Grade(query["id"], t, quality, True,
                     {"pred": pred, "gold": qg.data["valid"]})

    if t == "plan_construction":
        # The real grounding check: run the model's plan through the engine and
        # score it valid or not. This is where plan_construction tends to be 0.
        plan = extract_plan(answer_text)
        if plan is None:
            return Grade(query["id"], t, 0.0, True, {"parsed": False})
        plan.taken = list(query.get("taken", []))
        res = validate(plan, gold, snap, cfg) if cfg else validate(plan, gold, snap)
        terms_used = len(plan.terms)
        ref = qg.data.get("reference_terms")
        gap = (terms_used - ref) if ref is not None else None
        return Grade(query["id"], t, 1.0 if res.valid else 0.0, True,
                     {"parsed": True, "engine_valid": res.valid, "terms_used": terms_used,
                      "reference_terms": ref, "terms_gap": gap,
                      "failures": [str(f) for f in res.failures][:5]})

    raise ValueError(f"unknown query type {t}")
