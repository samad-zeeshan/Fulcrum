from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .corpus import Span, build_spans, load_snapshot
from .embedder import Embedder, get_embedder

class RagIndex:
    def __init__(self, spans: list[Span], vectors: np.ndarray, embedder_name: str,
                 snapshot_date: str = "", idf: np.ndarray | None = None):
        self.spans = spans
        self.vectors = vectors.astype(np.float32)
        self.embedder_name = embedder_name
        self.snapshot_date = snapshot_date
        self.idf = idf
        self._faiss = None
        self._build_faiss()

    def embedder(self):
        from .embedder import HashingEmbedder, SentenceTransformerEmbedder
        if self.embedder_name.startswith("hashing"):
            return HashingEmbedder(dim=int(self.vectors.shape[1]), idf=self.idf)
        return SentenceTransformerEmbedder(self.embedder_name)

    def _build_faiss(self):
        import faiss
        index = faiss.IndexFlatIP(self.vectors.shape[1])
        index.add(self.vectors)
        self._faiss = index

    @classmethod
    def build(cls, snapshot_path: str | Path, embedder: Embedder | None = None,
              subjects: set[str] | None = None) -> "RagIndex":
        snap = load_snapshot(snapshot_path)
        spans = build_spans(snap, subjects=subjects)
        embedder = embedder or get_embedder("auto")
        texts = [s.embed_text for s in spans]
        if hasattr(embedder, "fit_idf"):
            embedder.fit_idf(texts)
        vectors = embedder.encode(texts)
        idf = getattr(embedder, "idf", None)
        return cls(spans, vectors, embedder.name, snap.get("snapshot_date", ""), idf=idf)

    def save(self, out_dir: str | Path) -> None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        with (out / "spans.jsonl").open("w", encoding="utf-8") as fh:
            for s in self.spans:
                fh.write(json.dumps(asdict(s), ensure_ascii=False, sort_keys=True) + "\n")
        np.save(out / "vectors.npy", self.vectors)
        if self.idf is not None:
            np.save(out / "idf.npy", self.idf)
        (out / "meta.json").write_text(json.dumps({
            "embedder": self.embedder_name, "dim": int(self.vectors.shape[1]),
            "spans": len(self.spans), "snapshot_date": self.snapshot_date,
        }, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, in_dir: str | Path) -> "RagIndex":
        d = Path(in_dir)
        spans = [Span(**json.loads(ln)) for ln in (d / "spans.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
        vectors = np.load(d / "vectors.npy")
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        idf_path = d / "idf.npy"
        idf = np.load(idf_path) if idf_path.exists() else None
        return cls(spans, vectors, meta.get("embedder", ""), meta.get("snapshot_date", ""), idf=idf)

    def search(self, query_vec: np.ndarray, k: int = 5) -> list[tuple[Span, float]]:
        q = query_vec.reshape(1, -1).astype(np.float32)
        scores, idx = self._faiss.search(q, min(k, len(self.spans)))
        return [(self.spans[i], float(scores[0][rank])) for rank, i in enumerate(idx[0]) if i >= 0]
