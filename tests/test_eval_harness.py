import json
from pathlib import Path

import pytest
import yaml

from llm.provider import StubProvider
from planner import Gold, Snapshot
from eval.metrics.gold import compute_gold
from eval.metrics.grade import extract_plan, grade
from eval.metrics.harness import run_eval

ROOT = Path(__file__).resolve().parents[1]
SNAP1 = ROOT / "eval" / "snapshots" / "2026-06-28" / "offerings.json"

@pytest.fixture(scope="module")
def ctx():
    gold = Gold.load()
    snap = Snapshot.load(SNAP1)
    snap_dict = json.loads(SNAP1.read_text(encoding="utf-8"))
    return gold, snap, snap_dict

def _grade(query, answer, ctx, cited=None):
    gold, snap, snap_dict = ctx
    qg = compute_gold(query, gold, snap)
    return grade(query, qg, answer, snap_dict, gold, snap, cited_clauses=cited)

def test_grade_factual_offered(ctx):
    q = {"id": "o1", "type": "factual_offered", "course": "CMPUT 174", "term": "Fall Term 2026"}
    assert _grade(q, "Yes, CMPUT 174 is offered in Fall Term 2026.", ctx).quality == 1.0
    assert _grade(q, "No, it is not offered then.", ctx).quality == 0.0

def test_grade_factual_offered_negative_case(ctx):
    q = {"id": "o2", "type": "factual_offered", "course": "CMPUT 274", "term": "Winter Term 2027"}

    assert _grade(q, "No, CMPUT 274 is not offered in Winter Term 2027.", ctx).quality == 1.0

def test_grade_factual_prereq_recall(ctx):
    q = {"id": "p1", "type": "factual_prereq", "course": "CMPUT 204"}
    good = "CMPUT 204 requires CMPUT 175 or 275, CMPUT 272, and a calculus course like MATH 154."
    g = _grade(q, good, ctx)
    assert g.quality >= 0.6
    assert _grade(q, "No idea.", ctx).quality == 0.0

def test_grade_plan_validity(ctx):
    q = {"id": "v1", "type": "plan_validity", "plan_ref": "eval/plans/adv_six_400.plan.yaml"}
    assert _grade(q, "This plan is INVALID; the 300/400 pool is short.", ctx).quality == 1.0
    assert _grade(q, "Looks valid to me.", ctx).quality == 0.0

def test_grade_plan_validity_valid_plan(ctx):
    q = {"id": "v2", "type": "plan_validity", "plan_ref": "eval/plans/valid_174_stream.plan.yaml"}
    assert _grade(q, "Yes, this plan is valid and satisfies all requirements.", ctx).quality == 1.0

def test_extract_and_grade_constructed_plan(ctx):

    valid = yaml.safe_load((ROOT / "eval/plans/valid_174_stream.plan.yaml").read_text(encoding="utf-8"))
    answer = "Here is a plan:\n```yaml\n" + yaml.safe_dump({"terms": valid["terms"]}) + "\n```"
    assert extract_plan(answer) is not None
    q = {"id": "c1", "type": "plan_construction", "taken": []}
    g = _grade(q, answer, ctx)
    assert g.detail["parsed"] and g.quality == 1.0

    assert _grade(q, "just take some courses", ctx).quality == 0.0

def test_run_eval_stub_smoke():
    out = run_eval(SNAP1, provider=StubProvider(), embedder_kind="hashing", limit=6)
    assert set(out["configs"]) == {"RAG-always", "CAG-always", "Routed"}
    for agg in out["configs"].values():
        assert 0.0 <= agg["quality_overall"] <= 1.0
        assert agg["n"] == 6
    assert out["meta"]["is_stub"] is True
