from pathlib import Path

import pytest

from planner import Plan, validate

PLANS_DIR = Path(__file__).resolve().parents[1] / "eval" / "plans"
PLAN_FILES = sorted(PLANS_DIR.glob("*.plan.yaml"))

@pytest.mark.parametrize("path", PLAN_FILES, ids=[p.stem for p in PLAN_FILES])
def test_plan_matches_expected_verdict(path, gold, snap):
    plan = Plan.load(path)
    assert plan.expected in ("valid", "invalid"), f"{path.name} lacks expected verdict"
    result = validate(plan, gold, snap)

    expected_valid = plan.expected == "valid"
    assert result.valid is expected_valid, (
        f"{plan.plan_id}: expected {plan.expected}, got "
        f"{'valid' if result.valid else 'invalid'}; failures={[str(f) for f in result.failures]}"
    )

    blob = " | ".join(str(f) for f in result.failures)
    for needle in plan.expected_reasons:
        assert needle in blob, f"{plan.plan_id}: expected reason '{needle}' not in: {blob}"

def test_fixture_coverage_is_complete():
    verdicts = {Plan.load(p).expected for p in PLAN_FILES}
    assert "valid" in verdicts and "invalid" in verdicts
    names = {p.name for p in PLAN_FILES}
    assert any("adv_six_400" in n for n in names)
    assert any("prereq" in n for n in names)
    assert any("exclusion" in n for n in names)
