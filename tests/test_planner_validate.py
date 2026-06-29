from planner import Plan, PlanTerm, validate
from planner.config import EngineConfig

def _plan(terms, taken=None):
    return Plan(plan_id="t", terms=[PlanTerm(t, cs) for t, cs in terms], taken=taken or [])

def test_duplicate_course_detected(gold, snap):
    p = _plan([("Fall Term 2026", ["CMPUT 174"]), ("Winter Term 2027", ["CMPUT 174"])])
    r = validate(p, gold, snap)
    assert not r.valid and any(f.code == "duplicate_course" for f in r.failures)

def test_not_offered_detected(gold, snap):

    p = _plan([("Winter Term 2027", ["CMPUT 274"])])
    r = validate(p, gold, snap)
    assert any(f.code == "not_offered" and "CMPUT 274" in f.courses for f in r.failures)

def test_offered_exact_term_ok(gold, snap):

    p = _plan([("Fall Term 2026", ["CMPUT 274"])])
    r = validate(p, gold, snap)
    assert not any(f.code == "not_offered" for f in r.failures)

def test_prereq_ordering(gold, snap):

    p = _plan([("Fall Term 2026", ["CMPUT 175", "CMPUT 201"])])
    bad = validate(p, gold, snap)
    assert any(f.code == "prereq_unsatisfied" and "CMPUT 201" in f.courses for f in bad.failures)

    ok = _plan([("Fall Term 2026", ["CMPUT 175"]), ("Winter Term 2027", ["CMPUT 201"])])
    r = validate(ok, gold, snap)
    assert not any(f.code == "prereq_unsatisfied" for f in r.failures)

def test_coreq_same_term_ok(gold, snap):

    p = _plan([("Fall Term 2026", ["CMPUT 174"]),
               ("Winter Term 2027", ["CMPUT 175", "CMPUT 272"]),
               ("Fall Term 2027", ["CMPUT 291", "CMPUT 201"])])
    r = validate(p, gold, snap)
    assert not any(f.code == "coreq_unsatisfied" for f in r.failures)

def test_credit_exclusion(gold, snap):
    p = _plan([("Fall Term 2026", ["CMPUT 229"]), ("Winter Term 2027", ["E E 380"])])
    r = validate(p, gold, snap)
    assert any(f.code == "credit_exclusion" for f in r.failures)

def test_conditional_275_makes_201_ineligible(gold, snap):

    p = _plan([("Fall Term 2026", ["CMPUT 274"]),
               ("Winter Term 2027", ["CMPUT 275"]),
               ("Fall Term 2027", ["CMPUT 201"])])
    r = validate(p, gold, snap)
    assert "note1_275_blocks_201" in r.applied_conditionals
    assert not r.valid
    assert any(f.code in ("ineligible_course", "credit_exclusion") for f in r.failures)

def test_external_prereq_flag_changes_verdict(gold, snap):

    p = _plan([("Fall Term 2026", ["STAT 235"])])
    assumed = validate(p, gold, snap, EngineConfig(enforce_external_prereqs=False))
    enforced = validate(p, gold, snap, EngineConfig(enforce_external_prereqs=True))
    assert not any(f.code == "prereq_unsatisfied" for f in assumed.failures)
    assert any(f.code == "prereq_unsatisfied" and "STAT 235" in f.courses for f in enforced.failures)

def test_requires_snapshot(gold):
    import pytest
    with pytest.raises(ValueError):
        validate(_plan([("Fall Term 2026", ["CMPUT 174"])]), gold, None)
