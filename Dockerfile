# Lean image for the NP2 eval track (free-tier friendly).
# Core deps only — the deterministic hashing embedder means torch/sentence-transformers
# are OPTIONAL (add them for the real ST embedder). DeepSeek calls need DEEPSEEK_API_KEY
# at runtime; without it the harness runs the offline stub.
FROM python:3.12-slim

WORKDIR /app

# system libs faiss-cpu may need
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 make && rm -rf /var/lib/apt/lists/*

# core deps (no torch -> lean). For the real embedder: pip install sentence-transformers
RUN pip install --no-cache-dir \
        "ortools>=9.10" "pyyaml>=6.0" "numpy>=1.26" "faiss-cpu>=1.8" \
        "openai>=1.40" "langgraph>=0.2" "pytest>=8.0"

COPY . /app

# build the frozen-snapshot artifacts the eval needs
RUN python eval/snapshots/build_snapshot.py \
 && python eval/snapshots/make_synthetic_snapshot.py \
 && python eval/queries/build_queries.py \
 && python -m rag.build --embedder hashing

# default: run the offline eval (set DEEPSEEK_API_KEY and `make eval` for real metrics)
CMD ["python", "-m", "eval.metrics.harness", "--provider", "stub", "--embedder", "hashing"]
