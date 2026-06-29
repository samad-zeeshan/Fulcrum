"""
Three-way eval harness: runs RAG-always, CAG-always and Routed over the gold queries.

Grades each answer deterministically and writes per-query logs plus aggregate
quality, cost and latency.
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import asdict
from pathlib import Path

import yaml

from llm.provider import DeepSeekConfig, StubProvider, get_default_provider
from planner import Gold, Snapshot

from .configs import EvalConfigs
from .gold import compute_gold
from .grade import grade

REPO = Path(__file__).resolve().parents[2]
QUERIES = REPO / "eval" / "queries" / "queries.yaml"
DEFAULT_SNAPSHOT = REPO / "eval" / "snapshots" / "2026-06-28" / "offerings.json"
LOGS = REPO / "eval" / "logs"
REPORTS = REPO / "reports"

def _pct(xs, p):
    return round(statistics.quantiles(xs, n=100)[p - 1], 4) if len(xs) > 1 else (round(xs[0], 4) if xs else 0.0)

def run_eval(snapshot_path=DEFAULT_SNAPSHOT, provider=None, embedder_kind="hashing",
             limit=None, warm=3) -> dict:
    provider = provider or get_default_provider()
    gold = Gold.load()
    snap = Snapshot.load(snapshot_path)
    snap_dict = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    queries = yaml.safe_load(QUERIES.read_text(encoding="utf-8"))
    if limit:
        queries = queries[:limit]

    cfgs = EvalConfigs(snapshot_path, provider=provider, embedder_kind=embedder_kind, gold=gold)
    # Warm the cache before measuring so cost and latency reflect steady state.
    if provider.name == "deepseek":
        cfgs.warm(n=warm)

    # Precompute the gold verdict for every query from the engine/snapshot oracle.
    golds = {q["id"]: compute_gold(q, gold, snap) for q in queries}

    LOGS.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    for cfg_name, fn in cfgs.as_dict().items():
        rows = []
        log_fh = (LOGS / f"{cfg_name}.jsonl").open("w", encoding="utf-8")
        for q in queries:
            bundle = fn(q["text"])
            qg = golds[q["id"]]
            # A grader crash scores zero rather than killing the whole sweep.
            try:
                gr = grade(q, qg, bundle.text, snap_dict, gold, snap,
                           cited_clauses=bundle.cited_clauses)
            except Exception as e:
                from .grade import Grade
                gr = Grade(q["id"], q["type"], 0.0, True, {"grade_error": f"{type(e).__name__}: {e}"})
            row = {
                "config": cfg_name, "qid": q["id"], "type": q["type"], "route": bundle.route,
                "quality": gr.quality, "citation_ok": gr.citation_ok,
                "cost_usd": bundle.cost_usd, "latency_s": round(bundle.latency_s, 4),
                "cache_hit_tokens": bundle.usage.prompt_cache_hit_tokens,
                "prompt_tokens": bundle.usage.prompt_tokens,
                "completion_tokens": bundle.usage.completion_tokens,
                "answer": bundle.text[:500], "grade_detail": gr.detail,
            }
            rows.append(row)
            log_fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        log_fh.close()
        results[cfg_name] = _aggregate(cfg_name, rows)
        results[cfg_name]["_rows"] = rows

    meta = {
        "snapshot": Path(snapshot_path).parent.name,
        "snapshot_synthetic": bool(snap_dict.get("synthetic")),
        "provider": provider.name,
        "model": getattr(provider, "model", "stub"),
        "is_stub": provider.name == "stub",
        "embedder": cfgs.index.embedder_name,
        "n_queries": len(queries),
    }
    return {"meta": meta, "configs": results}

def _aggregate(name: str, rows: list[dict]) -> dict:
    by_type: dict[str, list[float]] = {}
    for r in rows:
        by_type.setdefault(r["type"], []).append(r["quality"])
    lat = [r["latency_s"] for r in rows]
    factual_offered = [r for r in rows if r["type"] == "factual_offered"]
    cit = [r["citation_ok"] for r in factual_offered]
    hit = sum(r["cache_hit_tokens"] for r in rows)
    prompt = sum(r["prompt_tokens"] for r in rows)
    return {
        "config": name,
        "quality_overall": round(statistics.mean([r["quality"] for r in rows]), 4) if rows else 0.0,
        "quality_by_type": {t: round(statistics.mean(v), 4) for t, v in sorted(by_type.items())},
        "citation_pass_rate": round(statistics.mean(cit), 4) if cit else None,
        "cost_usd_total": round(sum(r["cost_usd"] for r in rows), 6),
        "cost_usd_mean": round(statistics.mean([r["cost_usd"] for r in rows]), 8) if rows else 0.0,
        "latency_p50": _pct(lat, 50), "latency_p95": _pct(lat, 95),
        "cache_hit_rate": round(hit / prompt, 4) if prompt else 0.0,
        "n": len(rows),
    }

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--provider", choices=["auto", "deepseek", "stub"], default="auto")
    ap.add_argument("--embedder", default="hashing", help="hashing | st | auto")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if args.provider == "stub":
        provider = StubProvider()
    elif args.provider == "deepseek":
        from llm.provider import DeepSeekProvider
        provider = DeepSeekProvider()
    else:
        provider = get_default_provider()

    out = run_eval(args.snapshot, provider=provider, embedder_kind=args.embedder, limit=args.limit)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "results.json").write_text(
        json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "_rows"}
                    for k, v in out["configs"].items()} | {"meta": out["meta"]},
                   indent=2), encoding="utf-8")

    from .report import write_report
    drift = None
    try:
        from .drift import compute_drift
        drift = compute_drift()
    except Exception as e:
        print(f"  (drift skipped: {e})")
    write_report(out, drift=drift)
    print(f"eval done: provider={out['meta']['provider']} "
          f"({'STUB — illustrative' if out['meta']['is_stub'] else 'REAL'}); "
          f"snapshot={out['meta']['snapshot']}; report at reports/EVAL_REPORT.md")
    for name, agg in out["configs"].items():
        print(f"  {name:12s} quality={agg['quality_overall']:.3f} "
              f"cost=${agg['cost_usd_total']:.5f} p50={agg['latency_p50']}s "
              f"cache_hit={agg['cache_hit_rate']:.2f}")

if __name__ == "__main__":
    main()
