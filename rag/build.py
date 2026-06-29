from __future__ import annotations

import argparse
from pathlib import Path

from .embedder import get_embedder
from .index import RagIndex

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO / "eval" / "snapshots" / "2026-06-28" / "offerings.json"
DEFAULT_SUBJECTS = {"CMPUT", "MATH", "STAT"}

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--out", type=Path, default=None)

    ap.add_argument("--embedder", default="hashing", help="hashing | st | auto")
    ap.add_argument("--subjects", default=",".join(sorted(DEFAULT_SUBJECTS)),
                    help="comma-separated subjects, or 'all'")
    args = ap.parse_args()

    subjects = None if args.subjects == "all" else set(s.strip() for s in args.subjects.split(","))
    embedder = get_embedder(args.embedder)
    index = RagIndex.build(args.snapshot, embedder=embedder, subjects=subjects)

    date = index.snapshot_date or "snapshot"
    out = args.out or (REPO / "rag" / "index" / date)
    index.save(out)
    print(f"built RAG index: {len(index.spans)} spans, embedder={index.embedder_name}, "
          f"dim={index.vectors.shape[1]} -> {out}")

if __name__ == "__main__":
    main()
