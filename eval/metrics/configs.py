from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cag.answer import CagContext, answer_rules_query, warm_cache
from llm.provider import LLMProvider, StubProvider, Usage
from planner import Gold
from rag.answer import answer_offering_query
from rag.embedder import get_embedder
from rag.index import RagIndex
from rag.retriever import Retriever
from router.graph import Router

@dataclass
class AnswerBundle:
    text: str
    route: str
    retrieved_ids: list[str] = field(default_factory=list)
    cited_clauses: list[str] = field(default_factory=list)
    cost_usd: float = 0.0
    latency_s: float = 0.0
    usage: Usage = field(default_factory=Usage)

def _usage_of(*responses) -> Usage:
    u = Usage()
    for r in responses:
        if r is None:
            continue
        u.prompt_cache_hit_tokens += r.usage.prompt_cache_hit_tokens
        u.prompt_cache_miss_tokens += r.usage.prompt_cache_miss_tokens
        u.completion_tokens += r.usage.completion_tokens
    return u

class EvalConfigs:

    def __init__(self, snapshot_path: str | Path, provider: LLMProvider | None = None,
                 embedder_kind: str = "auto", k: int = 5, gold: Gold | None = None,
                 subjects=("CMPUT", "MATH", "STAT")):
        self.provider = provider or StubProvider()
        self.gold = gold or Gold.load()
        emb = get_embedder(embedder_kind)
        self.index = RagIndex.build(snapshot_path, embedder=emb, subjects=set(subjects))
        self.retriever = Retriever(self.index)
        self.cag_ctx = CagContext.from_gold(self.gold)
        self.router = Router(self.retriever, self.cag_ctx, self.provider, k=k)
        self.k = k

    def warm(self, n: int = 3):
        return warm_cache(self.cag_ctx, self.provider, n=n)

    def rag_always(self, query: str) -> AnswerBundle:
        a = answer_offering_query(query, self.retriever, self.provider, k=self.k)
        return AnswerBundle(text=a.text, route="rag", retrieved_ids=a.retrieved_ids,
                            cost_usd=a.cost_usd, latency_s=a.latency_s,
                            usage=a.response.usage if a.response else Usage())

    def cag_always(self, query: str) -> AnswerBundle:
        a = answer_rules_query(query, self.cag_ctx, self.provider)
        return AnswerBundle(text=a.text, route="cag", cited_clauses=a.cited_clauses,
                            cost_usd=a.cost_usd, latency_s=a.latency_s,
                            usage=a.response.usage if a.response else Usage())

    def routed(self, query: str) -> AnswerBundle:
        r = self.router.answer(query)
        return AnswerBundle(text=r.answer, route=r.route, retrieved_ids=r.retrieved_ids,
                            cited_clauses=r.cited_clauses, cost_usd=r.cost_usd,
                            latency_s=r.latency_s,
                            usage=_usage_of(r.rag.response if r.rag else None,
                                            r.cag.response if r.cag else None))

    def as_dict(self) -> dict:
        return {"RAG-always": self.rag_always,
                "CAG-always": self.cag_always,
                "Routed": self.routed}
