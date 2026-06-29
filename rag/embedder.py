"""
Turns span text into vectors for retrieval.

Default is a deterministic hashing TF-IDF so offline runs need no torch; a
sentence-transformers embedder is used instead when it is installed.
"""

from __future__ import annotations

import re
from typing import Protocol

import numpy as np

_TOKEN = re.compile(r"[a-z]+|\d{3}")

def _tokenize(text: str) -> list[str]:
    toks = _TOKEN.findall(text.lower())

    # Also emit a glued letter+number token so a course code like CMPUT 174
    # survives as one feature, not two unrelated ones.
    merged = []
    for i, t in enumerate(toks):
        merged.append(t)
        if i + 1 < len(toks) and t.isalpha() and toks[i + 1].isdigit():
            merged.append(t + toks[i + 1])
    return merged

def _l2norm(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (mat / norms).astype(np.float32)

class Embedder(Protocol):
    name: str
    dim: int

    def encode(self, texts: list[str]) -> np.ndarray: ...

# Deterministic bag-of-words vectors via feature hashing. No model download,
# so CI and offline eval work with no extra dependencies.
class HashingEmbedder:

    def __init__(self, dim: int = 1024, seed: int = 0, idf: np.ndarray | None = None):
        self.dim = dim
        self.seed = seed
        self.name = f"hashing-{dim}"
        self.idf = idf if idf is not None else np.ones(dim, dtype=np.float32)

    def _hash(self, token: str) -> int:
        h = 1469598103934665603 ^ self.seed
        for ch in token.encode():
            h = (h ^ ch) * 1099511628211 & 0xFFFFFFFFFFFFFFFF
        return h % self.dim

    def _tf(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        for tok in _tokenize(text):
            v[self._hash(tok)] += 1.0
        return v

    def fit_idf(self, texts: list[str]) -> "HashingEmbedder":
        df = np.zeros(self.dim, dtype=np.float32)
        for t in texts:
            present = np.zeros(self.dim, dtype=np.float32)
            for tok in set(_tokenize(t)):
                present[self._hash(tok)] = 1.0
            df += present
        n = max(1, len(texts))
        self.idf = np.log((1.0 + n) / (1.0 + df)).astype(np.float32) + 1.0
        return self

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            out[i] = self._tf(t) * self.idf
        return _l2norm(out)

class SentenceTransformerEmbedder:

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)
        self.name = model_name
        self.dim = self._model.get_sentence_embedding_dimension()

    def fit_idf(self, texts: list[str]):
        return self

    def encode(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return vecs.astype(np.float32)

def get_embedder(kind: str = "auto", **kw) -> Embedder:
    if kind in ("st", "sentence-transformers"):
        return SentenceTransformerEmbedder(**kw)
    if kind == "hashing":
        return HashingEmbedder(**kw)
    # auto prefers the dense model but falls back to hashing if it is missing.
    if kind == "auto":
        try:
            return SentenceTransformerEmbedder(**kw)
        except Exception:
            return HashingEmbedder()
    raise ValueError(f"unknown embedder kind: {kind}")
