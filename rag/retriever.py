from __future__ import annotations

from dataclasses import dataclass

from .corpus import Span
from .embedder import Embedder
from .index import RagIndex

@dataclass
class Retrieved:
    span: Span
    score: float

class Retriever:
    def __init__(self, index: RagIndex, embedder: Embedder | None = None):
        self.index = index

        self.embedder = embedder or index.embedder()

    def retrieve(self, query: str, k: int = 5) -> list[Retrieved]:
        qv = self.embedder.encode([query])[0]
        return [Retrieved(span=s, score=sc) for s, sc in self.index.search(qv, k=k)]
