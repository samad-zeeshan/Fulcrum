from __future__ import annotations

import argparse
from pathlib import Path

from .config import EngineConfig
from .gold import DEFAULT_GOLD, Gold
from .plan import Plan
from .snapshot import Snapshot
from .solve import solve
from .validate import validate

REPO = Path(__file__).resolve().parents[1]

def _latest_snapshot() -> Path:
    snaps = sorted((REPO / "eval" / "snapshots").glob("*/offerings.json"))
    if not snaps:
        raise SystemExit("no snapshot found; run eval/snapshots/build_snapshot.py")
    return snaps[-1]

def _config(args) -> EngineConfig:
    return EngineConfig(enforce_external_prereqs=args.enforce_external)

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="planner", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--snapshot", type=Path, default=None)
    ap.add_argument("--enforce-external", action="store_true",
                    help="enforce external prereqs (default: assume satisfiable)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="grade a plan YAML")
    pv.add_argument("plan", type=Path)

    ps = sub.add_parser("solve", help="build a reference plan")
    ps.add_argument("--taken", default="", help="comma-separated completed courses")

    args = ap.parse_args(argv)
    gold = Gold.load(args.gold)
    snap = Snapshot.load(args.snapshot or _latest_snapshot())
    cfg = _config(args)

    if args.cmd == "validate":
        result = validate(Plan.load(args.plan), gold, snap, cfg)
        print(f"plan: {Plan.load(args.plan).plan_id}")
        print(f"snapshot: {snap.date}")
        if result.applied_conditionals:
            print("conditionals applied:", ", ".join(result.applied_conditionals))
        print("VERDICT:", "VALID" if result.valid else "INVALID")
        for f in result.failures:
            print("  FAIL", f)
        for n in result.notes:
            print("  note", n)
        return 0 if result.valid else 1

    if args.cmd == "solve":
        taken = [c.strip() for c in args.taken.split(",") if c.strip()]
        res = solve(taken, gold, snap, cfg)
        print(f"snapshot: {snap.date}   status: {res.status}")
        if not res.found:
            print("no feasible plan within horizon")
            return 1
        print(f"terms-to-graduate: {res.terms_to_graduate}")
        for t in res.plan.terms:
            print(f"  {t.term}: {', '.join(t.courses)}")
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
