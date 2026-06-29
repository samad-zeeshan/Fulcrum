from planner.config import EngineConfig
from planner.expr import EvalContext, evaluate, referenced_courses

def _ctx(available, program, *, enforce=False, hs=True, patterns=()):
    return EvalContext(
        available=lambda c: c in available,
        is_program_course=lambda c: c in program,
        available_matching=lambda pat: any(p in available for p in patterns),
        cfg=EngineConfig(enforce_external_prereqs=enforce, hs_satisfied_by_admission=hs),
    )

def test_bare_course_available():
    assert evaluate("CMPUT 174", _ctx({"CMPUT 174"}, {"CMPUT 174"}))

def test_in_scope_course_missing_fails():

    assert not evaluate("CMPUT 175", _ctx(set(), {"CMPUT 175"}))

def test_external_assumed_when_not_enforced():

    assert evaluate("SCI 100", _ctx(set(), {"CMPUT 174"}, enforce=False))

def test_external_enforced_fails_when_absent():
    assert not evaluate("SCI 100", _ctx(set(), {"CMPUT 174"}, enforce=True))

def test_one_of_and_all_of():
    ctx = _ctx({"CMPUT 174", "CMPUT 272"}, {"CMPUT 174", "CMPUT 175", "CMPUT 272"})
    assert evaluate({"one_of": ["CMPUT 174", "CMPUT 175"]}, ctx)
    assert evaluate({"all_of": ["CMPUT 174", "CMPUT 272"]}, ctx)
    assert not evaluate({"all_of": ["CMPUT 174", "CMPUT 175"]}, ctx)

def test_hs_leaf():
    assert evaluate({"hs": "Mathematics 30-1"}, _ctx(set(), set(), hs=True))
    assert not evaluate({"hs": "Mathematics 30-1"}, _ctx(set(), set(), hs=False))

def test_pattern_leaf():
    ctx = _ctx({"CMPUT 201"}, set(), patterns=("CMPUT 201",))
    assert evaluate({"pattern": {"level_in": [200]}}, ctx)
    ctx_empty = _ctx(set(), set(), patterns=())
    assert not evaluate({"pattern": {"level_in": [200]}}, ctx_empty)

def test_none_is_satisfied():
    assert evaluate(None, _ctx(set(), set()))

def test_referenced_courses():
    expr = {"all_of": ["CMPUT 272", {"one_of": ["CMPUT 175", "CMPUT 275"]}, {"hs": "x"}]}
    assert referenced_courses(expr) == {"CMPUT 272", "CMPUT 175", "CMPUT 275"}
