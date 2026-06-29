from planner import Gold, Plan, PlanTerm, validate

def test_note1a_stream_substitution(gold: Gold):
    fc = gold.group("foundation_core")
    one_of_sets = [set(m["one_of"]) for m in fc.members if isinstance(m, dict) and "one_of" in m]
    assert {"CMPUT 174", "CMPUT 274"} in one_of_sets
    assert {"CMPUT 175", "CMPUT 275"} in one_of_sets

def test_note1b_275_blocks_201_broad(gold: Gold):
    cond = next(c for c in gold.conditionals if c.id == "note1_275_blocks_201")
    assert cond.when.get("taken") == "CMPUT 275"
    effects = cond.effects
    assert any(e.get("ineligible") == "CMPUT 201" for e in effects)
    mg = next(e["modify_group"] for e in effects if "modify_group" in e)
    assert mg["id"] == "senior_choice"

    assert mg["add_pattern"] == {"subject": "CMPUT", "level_gte": 200}

def test_note1b_honours_plan_validates(gold, snap):
    p = Plan.load("eval/plans/valid_275_honours_conditional.plan.yaml")
    r = validate(p, gold, snap)
    assert r.valid, [str(f) for f in r.failures]
    assert "note1_275_blocks_201" in r.applied_conditionals

def test_senior_pools_are_separate_and_additive(gold: Gold):
    ids = {g.id for g in gold.groups}
    assert {"senior_cmput_300_400", "senior_cmput_400"} <= ids
    g15 = gold.group("senior_cmput_300_400")
    g6 = gold.group("senior_cmput_400")
    assert g15.units_required == 15 and g6.units_required == 6

def test_implements_2026_not_2024_senior_core(gold, snap):
    p = Plan(plan_id="worksheet2024_senior_rule", terms=[
        PlanTerm("Fall Term 2026", ["CMPUT 174", "MATH 125", "MATH 154", "STAT 151"]),
        PlanTerm("Winter Term 2027", ["CMPUT 175", "MATH 136"]),
        PlanTerm("Fall Term 2027", ["CMPUT 201"]),
        PlanTerm("Winter Term 2028", ["CMPUT 229"]),
    ])
    r = validate(p, gold, snap)
    assert not r.valid
    unmet = " | ".join(f.detail for f in r.failures if f.code == "requirement_shortfall")
    assert "senior_required" in unmet

def test_catalog_year_is_2026_2027(gold: Gold):
    assert gold.program["catalog_year"] == "2026-2027"
