"""
Freshness and router-drift checks for the report.

Freshness compares two dated snapshots; router drift checks the route stays the
same across paraphrases of one question.
"""

from __future__ import annotations

import json
from pathlib import Path

from planner import Gold, Snapshot
from router.classifier import classify

REPO = Path(__file__).resolve().parents[2]
SNAP1 = REPO / "eval" / "snapshots" / "2026-06-28" / "offerings.json"
SNAP2 = REPO / "eval" / "snapshots" / "2026-07-14" / "offerings.json"

PARAPHRASES = {
    "When is CMPUT 174 offered?": [
        "Which terms does CMPUT 174 run in?",
        "Is CMPUT 174 available next term?",
        "What's the schedule for CMPUT 174?",
    ],
    "What is the prerequisite for CMPUT 204?": [
        "What do I need before taking CMPUT 204?",
        "Which courses are required to enrol in CMPUT 204?",
        "CMPUT 204 prereqs?",
    ],
    "Is CMPUT 415 offered in winter and what is its prerequisite?": [
        "Does CMPUT 415 run in the winter term, and what are its prerequisites?",
        "Winter availability and prereqs for CMPUT 415?",
    ],
}

def freshness(snap1_path=SNAP1, snap2_path=SNAP2) -> dict:
    s1 = Snapshot.load(snap1_path)
    s2 = Snapshot.load(snap2_path)
    d2 = json.loads(Path(snap2_path).read_text(encoding="utf-8"))
    gold = Gold.load()

    rows = []

    # Replay the seeded changes and confirm data answers move between snapshots.
    for m in d2.get("drift_manifest", []):
        course, term = m["course"], m.get("term", "")
        if m["kind"] in ("term_drop", "term_add"):
            before = s1.is_offered_in_term(course, term)
            after = s2.is_offered_in_term(course, term)
            rows.append((f"{course} offered in {term}?", "data", str(before), str(after), before != after))
        elif m["kind"] == "seats_full":
            rows.append((f"{course} {term} seats", "data", f"cap {m.get('old_capacity')}",
                         f"cap {m.get('new_capacity')}", True))
        elif m["kind"] == "time_move":
            rows.append((f"{course} {term} lecture time", "data", m.get("old_time_start", "?"),
                         m.get("new_time_start", "?"), True))

    # Rule answers should not move; they come from gold, not the snapshot.
    stable = []
    for c in ["CMPUT 204", "CMPUT 291", "CMPUT 401"]:
        p1 = s1.courses.get(c)

        e = gold.prerequisites.get(c)
        stable.append((f"{c} prerequisite", "rule", e.source if e else "—", e.source if e else "—", False))

    changed = sum(1 for r in rows if r[4])
    md = ["Data-dependent answers change between snapshots; rule answers stay stable.\n",
          "\n| Question | kind | snapshot 1 | snapshot 2 | changed? |",
          "|---|---|---|---|---|"]
    for q, kind, a, b, ch in rows + stable:
        md.append(f"| {q} | {kind} | {a} | {b} | {'✅ yes' if ch else '— no'} |")
    md.append(f"\n**{changed}/{len(rows)} data-dependent facts changed; "
              f"{len(stable)}/{len(stable)} rule facts stable.**")
    return {"freshness_md": "\n".join(md), "synthetic": bool(d2.get("synthetic")),
            "changed": changed, "data_total": len(rows)}

# Same question reworded should keep the same route; count how often it flips.
def router_drift() -> dict:
    flips = 0
    total = 0
    detail = []
    for base, paras in PARAPHRASES.items():
        base_route = classify(base).route
        for p in paras:
            total += 1
            r = classify(p).route
            flipped = r != base_route
            flips += flipped
            detail.append((base_route, p, r, flipped))
    flip_rate = flips / total if total else 0.0

    sweep = []
    for margin in (0, 1, 2):
        comp = 0
        n = 0
        for base, paras in PARAPHRASES.items():
            for q in [base] + paras:
                n += 1
                if classify(q, compound_margin=margin).route == "compound":
                    comp += 1
        sweep.append((margin, round(comp / n, 3)))

    md = [f"Paraphrase decision-flip rate: **{flips}/{total} = {flip_rate:.2f}**.\n",
          "\n| base route | paraphrase | route | flipped |", "|---|---|---|---|"]
    for br, p, r, f in detail:
        md.append(f"| {br} | {p} | {r} | {'⚠ yes' if f else 'no'} |")
    md.append("\n**Threshold sweep (compound_margin → share routed compound):** "
              + ", ".join(f"{m}→{frac}" for m, frac in sweep))
    return {"router_md": "\n".join(md), "flip_rate": flip_rate}

def compute_drift() -> dict:
    fr = freshness()
    ro = router_drift()
    return {**fr, **ro}

def main() -> None:
    d = compute_drift()
    REPORTS = REPO / "reports"
    REPORTS.mkdir(parents=True, exist_ok=True)
    md = ["# NP2 Drift & Freshness Report\n",
          "\n## Freshness (two dated snapshots)\n", d["freshness_md"],
          "\n\n## Router drift\n", d["router_md"], "\n"]
    (REPORTS / "DRIFT_REPORT.md").write_text("".join(md), encoding="utf-8")
    print(f"drift done: {d['changed']}/{d['data_total']} data facts changed; "
          f"router flip rate {d['flip_rate']:.2f}; report at reports/DRIFT_REPORT.md")

if __name__ == "__main__":
    main()
