import inspect
from pathlib import Path

import pytest

from cag import CagContext
from llm.provider import StubProvider
from planner import Gold
from rag import RagIndex, Retriever
from rag.embedder import HashingEmbedder
from router import Router, classify

ROOT = Path(__file__).resolve().parents[1]
SNAP1 = ROOT / "eval" / "snapshots" / "2026-06-28" / "offerings.json"

@pytest.fixture(scope="module")
def router() -> Router:
    gold = Gold.load()
    idx = RagIndex.build(SNAP1, embedder=HashingEmbedder(), subjects={"CMPUT", "MATH", "STAT"})
    return Router(Retriever(idx), CagContext.from_gold(gold), StubProvider())

@pytest.mark.parametrize("q,expected", [
    ("When is CMPUT 174 offered next term?", "rag"),
    ("What are the lecture times and seats for CMPUT 204?", "rag"),
    ("What is the prerequisite for CMPUT 291?", "cag"),
    ("How many units does the senior requirement need?", "cag"),
    ("Is CMPUT 415 offered in winter and what is its prerequisite?", "compound"),
])
def test_classify_routes(q, expected):
    assert classify(q).route == expected

def test_classify_is_explainable():
    d = classify("When is CMPUT 174 offered?")
    assert "offering" in d.explanation and d.offering_score > 0

def test_router_rag_route(router):
    res = router.answer("When is CMPUT 174 offered?")
    assert res.route == "rag"
    assert res.rag is not None and res.cag is None
    assert res.retrieved_ids

def test_router_cag_route(router):
    res = router.answer("What is the prerequisite for CMPUT 291?")
    assert res.route == "cag"
    assert res.cag is not None and res.rag is None

def test_router_compound_calls_both(router):
    res = router.answer("Is CMPUT 415 offered in winter and what is its prerequisite?")
    assert res.route == "compound"
    assert res.rag is not None and res.cag is not None
    assert "Rules:" in res.answer and "Offerings:" in res.answer

def test_compound_does_not_call_engine():
    import router.graph as g
    src = inspect.getsource(g)
    assert "import planner" not in src and "from planner" not in src
