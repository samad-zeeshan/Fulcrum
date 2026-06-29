"""
RAG path: retrieve offering spans and answer the question from them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from llm.provider import LLMProvider, LLMResponse, StubProvider

from .retriever import Retrieved, Retriever

# Answer only from the retrieved context and cite span ids, so replies stay grounded.
SYSTEM = (
    "You are a University of Alberta course-offerings assistant. Answer ONLY using "
    "the provided context lines, each tagged with a [span-id]. If the context does "
    "not contain the answer, say you don't have that information. Cite the [span-id] "
    "of every fact you use. Be concise."
)

@dataclass
class RagAnswer:
    query: str
    text: str
    retrieved_ids: list[str]
    contexts: list[str]
    response: LLMResponse | None = None
    extra: dict = field(default_factory=dict)

    @property
    def cost_usd(self) -> float:
        return self.response.cost_usd if self.response else 0.0

    @property
    def latency_s(self) -> float:
        return self.response.latency_s if self.response else 0.0

def build_prompt(query: str, retrieved: list[Retrieved]) -> str:
    ctx = "\n".join(r.span.text for r in retrieved)
    return f"Context:\n{ctx}\n\nQuestion: {query}\nAnswer (cite [span-id]s):"

def answer_offering_query(query: str, retriever: Retriever,
                          provider: LLMProvider | None = None, k: int = 5) -> RagAnswer:
    provider = provider or StubProvider()
    retrieved = retriever.retrieve(query, k=k)
    user = build_prompt(query, retrieved)
    resp = provider.complete(SYSTEM, user)
    return RagAnswer(
        query=query,
        text=resp.text,
        retrieved_ids=[r.span.id for r in retrieved],
        contexts=[r.span.text for r in retrieved],
        response=resp,
        extra={"scores": [r.score for r in retrieved]},
    )
