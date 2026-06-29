from pathlib import Path

from planner import Plan, validate
from planner.matching import match_requirements
from planner.requirements import build_requirements, units_of

PLANS = Path(__file__).resolve().parents[1] / "eval" / "plans"

def _naive_bucket_satisfies(earned, gold, snap) -> bool:
    for g in gold.groups:
        if g.type == "all_of":
            for member in g.members:
                opts = {member} if isinstance(member, str) else set(member["one_of"])
                if not (opts & earned):
                    return False
        elif g.type == "units_from":
            have = sum(units_of(gold, snap, c) for c in earned if c in set(g.options))
            if have < g.units_required:
                return False
        elif g.type == "units_from_pattern":
            have = sum(units_of(gold, snap, c) for c in earned if snap.matches_pattern(c, g.pattern))
            if have < g.units_required:
                return False
    return True

def test_adversarial_defeats_bucket_counter(gold, snap):
    plan = Plan.load(PLANS / "adv_six_400.plan.yaml")
    earned = set(plan.all_courses())

    assert _naive_bucket_satisfies(earned, gold, snap) is True

    result = validate(plan, gold, snap)
    assert result.valid is False
    codes = {f.code for f in result.failures}
    assert "requirement_shortfall" in codes

    assert any("senior_cmput_300_400" in f.detail for f in result.failures)

def test_distinctness_one_course_one_slot(gold, snap):

    reqs = build_requirements(gold, set())
    res = match_requirements({"CMPUT 300"}, reqs, gold, snap, _cfg())
    assigned_to = [s.slot_id for s in res.slots for c in s.assigned if c == "CMPUT 300"]
    assert len(assigned_to) <= 1

def test_full_valid_set_matches(gold, snap):
    plan = Plan.load(PLANS / "valid_174_stream.plan.yaml")
    reqs = build_requirements(gold, set(plan.all_courses()))
    res = match_requirements(set(plan.all_courses()), reqs, gold, snap, _cfg())
    assert res.satisfied is True
    assert res.unmet() == []

def _cfg():
    from planner.config import DEFAULT_CONFIG
    return DEFAULT_CONFIG
