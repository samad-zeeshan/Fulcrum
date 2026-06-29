import os
import random

from dataclasses import replace

from planner import Plan, PlanTerm, solve, validate
from planner.config import DEFAULT_CONFIG
from planner.matching import match_requirements
from planner.requirements import build_requirements

ROUND_TRIP_CASES = int(os.environ.get("FULCRUM_ROUNDTRIP_CASES", "150"))
SEED = 20260628

SCOPED = replace(DEFAULT_CONFIG, restrict_candidates_to_scope=True)

def _sanitise(taken: set[str], gold) -> set[str]:
    taken = set(taken)
    for excl in gold.credit_exclusions:
        present = [c for c in excl.courses if c in taken]
        for extra in present[1:]:
            taken.discard(extra)
    if "CMPUT 275" in taken:
        taken.discard("CMPUT 201")
    return taken

def test_round_trip_solve_output_always_validates(gold, snap):
    rng = random.Random(SEED)
    pool = sorted(gold.eval_scope())
    failures = []
    for i in range(ROUND_TRIP_CASES):
        k = rng.randint(0, 10)
        taken = _sanitise(set(rng.sample(pool, k)), gold)
        res = solve(taken=taken, gold=gold, snap=snap, cfg=SCOPED)
        if not res.found:
            failures.append((i, sorted(taken), "solve found no plan"))
            continue
        v = validate(res.plan, gold, snap, SCOPED)
        if not v.valid:
            failures.append((i, sorted(taken), [str(f) for f in v.failures]))
    assert not failures, f"{len(failures)}/{ROUND_TRIP_CASES} round-trip failures: {failures[:3]}"

def test_round_trip_from_scratch_and_partial(gold, snap):

    for taken in ([], ["CMPUT 174", "CMPUT 175", "MATH 125", "MATH 154", "MATH 136", "STAT 151"]):
        res = solve(taken=taken, gold=gold, snap=snap)
        assert res.found
        assert validate(res.plan, gold, snap).valid

def test_property_distinctness_blocks_double_count(gold, snap):
    reqs = build_requirements(gold, set())
    two_400 = {"CMPUT 401", "CMPUT 402"}
    res = match_requirements(two_400, reqs, gold, snap, DEFAULT_CONFIG)

    for c in two_400:
        slots = [s.slot_id for s in res.slots if c in s.assigned]
        assert len(slots) <= 1

    pool15 = next(s for s in res.slots if s.group_id == "senior_cmput_300_400")
    assert pool15.shortfall_units > 0

def test_property_missing_one_group_localises(gold, snap):
    valid = Plan.load("eval/plans/valid_174_stream.plan.yaml")
    earned = set(valid.all_courses())
    earned.discard("MATH 136")
    reqs = build_requirements(gold, earned)
    res = match_requirements(earned, reqs, gold, snap, DEFAULT_CONFIG)
    unmet = {s.group_id for s in res.unmet()}
    assert "foundation_calc_2" in unmet
    assert unmet == {"foundation_calc_2"}

def test_property_credit_exclusion_rejects_two_from_set(gold, snap):
    p = Plan(plan_id="x", terms=[PlanTerm("Fall Term 2026", ["CMPUT 229"]),
                                  PlanTerm("Winter Term 2027", ["E E 380"])])
    r = validate(p, gold, snap)
    assert any(f.code == "credit_exclusion" for f in r.failures)

def test_property_conditional_rewrites_senior_choice(gold, snap):
    reqs = build_requirements(gold, {"CMPUT 275"})
    assert "note1_275_blocks_201" in reqs.applied_conditionals
    assert "CMPUT 201" in reqs.ineligible
    sc = next(s for s in reqs.slots if s.group_id == "senior_choice")
    assert sc.options == frozenset({"CMPUT 229", "CMPUT 291"})
    assert sc.pattern == {"subject": "CMPUT", "level_gte": 200}

    base = build_requirements(gold, set())
    sc0 = next(s for s in base.slots if s.group_id == "senior_choice")
    assert "CMPUT 201" in sc0.options
    assert "CMPUT 201" not in base.ineligible

def test_decisions_are_locked(gold):
    assert gold.program["catalog_year"] == "2026-2027"
    assert gold.prerequisites["CMPUT 300"].confidence == "resolved"
    assert DEFAULT_CONFIG.enforce_external_prereqs is False

def test_bridge_scope_is_present_and_spans_levels(gold, snap):
    bridge = gold.bridge_courses()
    assert len(bridge) >= 8
    levels = {snap.level_of(c) for c in bridge}
    assert 300 in levels and 400 in levels

    for c in bridge:
        assert gold.prerequisites[c].source, f"{c} missing verbatim source"
