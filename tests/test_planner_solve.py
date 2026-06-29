from planner import solve, validate
from planner.config import EngineConfig

def test_solve_from_scratch_is_valid(gold, snap):
    res = solve(taken=[], gold=gold, snap=snap)
    assert res.found

    v = validate(res.plan, gold, snap)
    assert v.valid, [str(f) for f in v.failures]

    assert res.terms_to_graduate >= 4

def test_solve_respects_taken_courses(gold, snap):
    taken = ["CMPUT 174", "CMPUT 175", "MATH 125", "MATH 154", "MATH 136", "STAT 151"]
    res = solve(taken=taken, gold=gold, snap=snap)
    assert res.found

    scheduled = set(res.plan.scheduled_courses())
    assert not (scheduled & set(taken))

    full = solve(taken=[], gold=gold, snap=snap)
    assert res.terms_to_graduate <= full.terms_to_graduate

def test_solve_plan_validates_under_same_config(gold, snap):
    cfg = EngineConfig(enforce_external_prereqs=False, max_units_per_term=12.0)
    res = solve(taken=[], gold=gold, snap=snap, cfg=cfg)
    assert res.found

    for t in res.plan.terms:
        load = sum(snap.units_of(c) for c in t.courses)
        assert load <= 12.0 + 1e-9
    assert validate(res.plan, gold, snap, cfg).valid

def test_solve_is_deterministic(gold, snap):
    a = solve(taken=[], gold=gold, snap=snap)
    b = solve(taken=[], gold=gold, snap=snap)
    assert a.terms_to_graduate == b.terms_to_graduate
    assert a.chosen == b.chosen
