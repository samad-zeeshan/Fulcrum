import json
from pathlib import Path

import pytest

from llm.provider import StubProvider
from rag import (
    RagIndex,
    Retriever,
    answer_offering_query,
    audit_offering_answer,
)
from rag.embedder import HashingEmbedder

ROOT = Path(__file__).resolve().parents[1]
SNAP1 = ROOT / "eval" / "snapshots" / "2026-06-28" / "offerings.json"
SNAP2 = ROOT / "eval" / "snapshots" / "synthetic_demo" / "offerings.json"

@pytest.fixture(scope="module")
def index() -> RagIndex:
    return RagIndex.build(SNAP1, embedder=HashingEmbedder(), subjects={"CMPUT", "MATH", "STAT"})

@pytest.fixture(scope="module")
def snap1() -> dict:
    return json.loads(SNAP1.read_text(encoding="utf-8"))

def test_retrieval_finds_the_right_course(index):
    r = Retriever(index)
    hits = r.retrieve("When is CMPUT 174 offered and what are the lecture times?", k=5)
    assert any("CMPUT 174" in h.span.id for h in hits)

def test_retrieval_offering_term_query(index):

    r = Retriever(index)
    hits = r.retrieve("What are the CMPUT 204 lecture times and seats?", k=5)
    assert any(h.span.course == "CMPUT 204" for h in hits[:3])
    assert any(h.span.kind == "offering" and h.span.course == "CMPUT 204" for h in hits)

def test_index_roundtrip_save_load(index, tmp_path):
    index.save(tmp_path / "idx")
    loaded = RagIndex.load(tmp_path / "idx")
    assert len(loaded.spans) == len(index.spans)

    hits = Retriever(loaded).retrieve("CMPUT 204 algorithms", k=3)
    assert any("CMPUT 204" in h.span.id for h in hits)

def test_citation_audit_passes_truthful_answer(snap1):

    ans = "CMPUT 174 is offered in Fall Term 2026; a lecture meets at 10:00."
    assert audit_offering_answer(ans, snap1).ok

def test_citation_audit_fails_wrong_term(snap1):
    ans = "CMPUT 174 is offered in Spring Term 2099."
    res = audit_offering_answer(ans, snap1)
    assert not res.ok and any("term" in v for v in res.violations)

def test_citation_audit_fails_wrong_time(snap1):
    ans = "CMPUT 291 lectures meet at 07:07."
    res = audit_offering_answer(ans, snap1)
    assert not res.ok and any("time" in v for v in res.violations)

def test_rag_answer_logs_usage_with_stub(index):
    r = Retriever(index)
    ans = answer_offering_query("When is CMPUT 204 offered?", r, provider=StubProvider(), k=4)
    assert ans.retrieved_ids and len(ans.retrieved_ids) <= 4
    assert ans.response is not None
    assert ans.response.usage.prompt_tokens > 0
    assert ans.cost_usd == 0.0

def test_citation_audit_catches_snapshot_drift(snap1):
    snap2 = json.loads(SNAP2.read_text(encoding="utf-8"))
    ans = "CMPUT 304 is offered in Fall Term 2026."
    assert audit_offering_answer(ans, snap1).ok
    assert not audit_offering_answer(ans, snap2).ok
