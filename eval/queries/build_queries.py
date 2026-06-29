from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SNAP1 = REPO / "eval" / "snapshots" / "2026-06-28" / "offerings.json"
GOLD = REPO / "eval" / "gold" / "cs_major.gold.yaml"
PLANS = REPO / "eval" / "plans"
OUT = REPO / "eval" / "queries" / "queries.yaml"

OFFERED_QUERIES = [
    ("CMPUT 174", "Fall Term 2026"),
    ("CMPUT 174", "Spring Term 2026"),
    ("CMPUT 274", "Winter Term 2027"),
    ("CMPUT 275", "Fall Term 2026"),
    ("CMPUT 304", "Fall Term 2026"),
    ("CMPUT 333", "Winter Term 2027"),
    ("CMPUT 333", "Fall Term 2026"),
    ("CMPUT 401", "Winter Term 2027"),
    ("CMPUT 402", "Fall Term 2026"),
    ("CMPUT 455", "Winter Term 2027"),
    ("CMPUT 461", "Fall Term 2026"),
    ("CMPUT 291", "Fall Term 2026"),
    ("CMPUT 200", "Fall Term 2026"),
    ("CMPUT 229", "Winter Term 2027"),
    ("MATH 125", "Winter Term 2027"),
    ("MATH 136", "Fall Term 2026"),
    ("STAT 151", "Fall Term 2026"),
    ("STAT 265", "Spring Term 2026"),
    ("CMPUT 350", "Winter Term 2027"),
    ("CMPUT 355", "Fall Term 2026"),
]

PREREQ_COURSES = ["CMPUT 175", "CMPUT 201", "CMPUT 204", "CMPUT 229", "CMPUT 272",
                  "CMPUT 291", "CMPUT 300", "CMPUT 301", "CMPUT 303", "CMPUT 331",
                  "CMPUT 333", "CMPUT 350", "CMPUT 401", "CMPUT 402", "CMPUT 461",
                  "STAT 235"]

TAKEN_SETS = [
    [],
    ["CMPUT 174", "CMPUT 175", "MATH 125", "MATH 154", "MATH 136", "STAT 151"],
    ["CMPUT 174", "MATH 125"],
    ["CMPUT 274", "CMPUT 275", "MATH 125", "MATH 154", "MATH 136", "STAT 151", "CMPUT 272"],
]

def _plan_text(plan: dict) -> str:
    rows = []
    for t in plan.get("terms", []):
        rows.append(f"{t['term']}: {', '.join(t.get('courses', []))}")
    taken = plan.get("taken") or []
    pre = f"Already completed: {', '.join(taken)}. " if taken else ""
    return pre + " | ".join(rows)

def build() -> list[dict]:
    queries: list[dict] = []

    for i, (course, term) in enumerate(OFFERED_QUERIES):
        queries.append({
            "id": f"factual_offered_{i:03d}", "type": "factual_offered",
            "text": f"Is {course} offered in {term}?",
            "course": course, "term": term,
        })

    for i, course in enumerate(PREREQ_COURSES):
        queries.append({
            "id": f"factual_prereq_{i:03d}", "type": "factual_prereq",
            "text": f"What is the prerequisite for {course}?",
            "course": course,
        })

    for i, pf in enumerate(sorted(PLANS.glob("*.plan.yaml"))):
        plan = yaml.safe_load(pf.read_text(encoding="utf-8"))
        queries.append({
            "id": f"plan_validity_{i:03d}", "type": "plan_validity",
            "text": f"Is the following Computing Science major plan valid? {_plan_text(plan)}",
            "plan_ref": pf.relative_to(REPO).as_posix(),
        })

    for i, taken in enumerate(TAKEN_SETS):
        done = f" I have already completed: {', '.join(taken)}." if taken else " I am starting fresh."
        queries.append({
            "id": f"plan_construction_{i:03d}", "type": "plan_construction",
            "text": (f"Build a course plan that completes the Computing Science major in as few terms "
                     f"as possible.{done} Use alternating Fall and Winter terms (label them 'Fall' / "
                     f"'Winter'). Only place a course in a term in which it is offered, and respect "
                     f"prerequisites (a prerequisite must be in an earlier term). Output ONLY YAML with a "
                     f"'terms' list, each item having a 'term' and a list of 'courses'."),
            "taken": taken,
        })

    return queries

def main() -> None:
    queries = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(queries, sort_keys=False, allow_unicode=True), encoding="utf-8")
    by_type: dict[str, int] = {}
    for q in queries:
        by_type[q["type"]] = by_type.get(q["type"], 0) + 1
    print(f"wrote {OUT}  ({len(queries)} queries: {json.dumps(by_type)})")

if __name__ == "__main__":
    main()
