from __future__ import annotations

import sys
from pathlib import Path

from cag.answer import CagContext
from llm.provider import get_default_provider
from planner import Gold
from rag.embedder import HashingEmbedder
from rag.index import RagIndex
from rag.retriever import Retriever
from router.graph import Router

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO / "eval" / "snapshots" / "2026-06-28" / "offerings.json"

def _build_router() -> Router:
    gold = Gold.load()
    index = RagIndex.build(SNAPSHOT, embedder=HashingEmbedder(), subjects={"CMPUT", "MATH", "STAT"})
    provider = get_default_provider()
    return Router(Retriever(index), CagContext.from_gold(gold), provider)

def _ask(router: Router, q: str) -> None:
    res = router.answer(q)
    print(f"\nQ: {q}")
    print(f"  route   : {res.route}   ({res.decision.explanation})")
    print(f"  answer  : {res.answer.strip()}")
    if res.retrieved_ids:
        print(f"  RAG span: {res.retrieved_ids[:3]}")
    if res.cited_clauses:
        print(f"  CAG cite: {res.cited_clauses[:5]}")
    print(f"  cost    : ${res.cost_usd:.6f}   latency: {res.latency_s:.2f}s")

def main() -> None:
    router = _build_router()
    prov = router.provider.name
    print(f"router ready (provider={prov}{' — OFFLINE STUB, set DEEPSEEK_API_KEY for real answers' if prov=='stub' else ''})")
    args = [a for a in sys.argv[1:]]
    if args:
        _ask(router, " ".join(args))
        return
    print("Type a question (blank line to quit).")
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        _ask(router, q)

if __name__ == "__main__":
    main()
