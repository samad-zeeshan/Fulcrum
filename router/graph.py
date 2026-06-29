"""
LangGraph wiring of the router: classify, then branch to rag, cag or compound.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from cag.answer import CagAnswer, CagContext, answer_rules_query
from llm.provider import LLMProvider, StubProvider
from rag.answer import RagAnswer, answer_offering_query
from rag.retriever import Retriever

from .classifier import RouteDecision, classify

class _State(TypedDict, total=False):
    query: str
    decision: RouteDecision
    rag: Optional[RagAnswer]
    cag: Optional[CagAnswer]
    answer: str

@dataclass
class RouterResult:
    query: str
    route: str
    answer: str
    decision: RouteDecision
    rag: RagAnswer | None = None
    cag: CagAnswer | None = None
    extra: dict = field(default_factory=dict)

    @property
    def cost_usd(self) -> float:
        return (self.rag.cost_usd if self.rag else 0.0) + (self.cag.cost_usd if self.cag else 0.0)

    @property
    def latency_s(self) -> float:

        return (self.rag.latency_s if self.rag else 0.0) + (self.cag.latency_s if self.cag else 0.0)

    @property
    def retrieved_ids(self) -> list[str]:
        return self.rag.retrieved_ids if self.rag else []

    @property
    def cited_clauses(self) -> list[str]:
        return self.cag.cited_clauses if self.cag else []

class Router:
    def __init__(self, retriever: Retriever, cag_ctx: CagContext,
                 provider: LLMProvider | None = None, k: int = 5,
                 compound_margin: int = 1):
        self.retriever = retriever
        self.cag_ctx = cag_ctx
        self.provider = provider or StubProvider()
        self.k = k
        self.compound_margin = compound_margin
        self._graph = self._build()

    def _classify(self, s: _State) -> _State:
        return {"decision": classify(s["query"], compound_margin=self.compound_margin)}

    def _rag(self, s: _State) -> _State:
        a = answer_offering_query(s["query"], self.retriever, self.provider, k=self.k)
        return {"rag": a, "answer": a.text}

    def _cag(self, s: _State) -> _State:
        a = answer_rules_query(s["query"], self.cag_ctx, self.provider)
        return {"cag": a, "answer": a.text}

    def _compound(self, s: _State) -> _State:
        # Run both paths and stitch the rules and offerings answers together.
        cag = answer_rules_query(s["query"], self.cag_ctx, self.provider)
        rag = answer_offering_query(s["query"], self.retriever, self.provider, k=self.k)
        combined = f"Rules: {cag.text}\nOfferings: {rag.text}"
        return {"cag": cag, "rag": rag, "answer": combined}

    def _build(self):
        g = StateGraph(_State)
        g.add_node("classify", self._classify)
        g.add_node("rag", self._rag)
        g.add_node("cag", self._cag)
        g.add_node("compound", self._compound)
        g.set_entry_point("classify")
        # Branch on the classifier's chosen route.
        g.add_conditional_edges("classify", lambda s: s["decision"].route,
                                {"rag": "rag", "cag": "cag", "compound": "compound"})
        for n in ("rag", "cag", "compound"):
            g.add_edge(n, END)
        return g.compile()

    def answer(self, query: str) -> RouterResult:
        out: dict[str, Any] = self._graph.invoke({"query": query})
        dec = out["decision"]
        return RouterResult(query=query, route=dec.route, answer=out.get("answer", ""),
                            decision=dec, rag=out.get("rag"), cag=out.get("cag"))
