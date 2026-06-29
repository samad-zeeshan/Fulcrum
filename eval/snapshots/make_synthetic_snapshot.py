from __future__ import annotations

import argparse
import copy
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SNAP1 = REPO / "eval" / "snapshots" / "2026-06-28" / "offerings.json"

DRIFT = [

    {"course": "CMPUT 174", "kind": "seats_full", "term": "Fall Term 2026", "component": "LECTURE"},

    {"course": "CMPUT 291", "kind": "time_move", "term": "Winter Term 2027", "component": "LECTURE",
     "new_time_start": "13:00", "new_time_end": "14:20"},

    {"course": "CMPUT 304", "kind": "term_drop", "term": "Fall Term 2026"},

    {"course": "CMPUT 461", "kind": "term_add", "term": "Winter Term 2027",
     "component": "LECTURE", "capacity": 60, "days": ["T", "R"],
     "time_start": "11:00", "time_end": "12:20"},
]

def _apply_drift(courses: dict, manifest_out: list) -> None:
    for d in DRIFT:
        c = courses.get(d["course"])
        if c is None:
            continue
        kind = d["kind"]
        if kind == "seats_full":
            for s in c["sections"]:
                if s["term"] == d["term"] and s["component"] == d["component"]:
                    manifest_out.append({**d, "old_capacity": s["capacity"], "new_capacity": 0})
                    s["capacity"] = 0
                    break
        elif kind == "time_move":
            for s in c["sections"]:
                if s["term"] == d["term"] and s["component"] == d["component"] and s["meetings"]:
                    m = s["meetings"][0]
                    manifest_out.append({**d, "old_time_start": m["time_start"]})
                    m["time_start"] = d["new_time_start"]
                    m["time_end"] = d["new_time_end"]
                    break
        elif kind == "term_drop":
            had = d["term"] in c["terms"]
            c["terms"] = [t for t in c["terms"] if t != d["term"]]
            c["sections"] = [s for s in c["sections"] if s["term"] != d["term"]]
            manifest_out.append({**d, "was_offered": had, "now_offered": d["term"] in c["terms"]})
        elif kind == "term_add":
            if d["term"] not in c["terms"]:
                c["terms"].append(d["term"])
            c["sections"].append({
                "term": d["term"], "component": d["component"], "section": "A1",
                "class_id": f"SYN{abs(hash(d['course'])) % 90000 + 10000}", "capacity": d["capacity"],
                "meetings": [{"days": d["days"], "time_start": d["time_start"],
                              "time_end": d["time_end"], "date_start": None, "date_end": None}],
            })
            manifest_out.append({**d, "now_offered": True})

def _registration_decay(courses: dict, rng: random.Random) -> int:
    touched = 0
    for c in courses.values():
        for s in c["sections"]:
            cap = s.get("capacity")
            if not cap or rng.random() > 0.4:
                continue
            drop = rng.randint(1, max(1, cap // 3))
            s["capacity"] = max(0, cap - drop)
            touched += 1
    return touched

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="src", type=Path, default=SNAP1)
    ap.add_argument("--date", default="2026-07-14", help="synthetic snapshot date")
    ap.add_argument("--seed", type=int, default=20260714)
    args = ap.parse_args()

    snap = json.loads(args.src.read_text(encoding="utf-8"))
    snap = copy.deepcopy(snap)
    rng = random.Random(args.seed)

    manifest: list = []
    _apply_drift(snap["courses"], manifest)
    decayed = _registration_decay(snap["courses"], rng)

    snap["snapshot_date"] = args.date
    snap["synthetic"] = True
    snap["derived_from"] = args.src.relative_to(REPO).as_posix()
    snap["source"] = (f"SYNTHETIC drift of {args.src.name} (seed {args.seed}); "
                      f"{len(manifest)} explicit changes + {decayed} capacity nudges. "
                      "NOT a real re-scrape — replace before sharing for the strongest freshness claim.")
    snap["drift_manifest"] = manifest

    out = REPO / "eval" / "snapshots" / args.date / "offerings.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}  (synthetic; {len(manifest)} explicit drifts, {decayed} capacity nudges)")
    for m in manifest:
        print("  drift:", m["course"], m["kind"], m.get("term", ""))

if __name__ == "__main__":
    main()
