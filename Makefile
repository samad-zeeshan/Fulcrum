# Fulcrum / NP2 — make targets.
# Phase A (constraint engine) targets are live; later phases add `eval` and `drift`.

PYTHON ?= python

.PHONY: help engine-test test snapshot validate solve clean

help:
	@echo "engine-test   run the constraint-engine tests (incl. the adversarial plan)"
	@echo "test          run the full pytest suite (scraper + engine + eval track)"
	@echo "snapshot      (re)build the frozen offerings snapshot from corpus/"
	@echo "snapshot2     build the synthetic second snapshot (freshness demo)"
	@echo "queries       (re)generate the gold query set"
	@echo "rag-build     build the RAG FAISS index from the snapshot"
	@echo "eval          run the eval harness (real if DEEPSEEK_API_KEY set, else stub) -> reports/"
	@echo "eval-stub     run the eval harness offline (stub provider, hashing embedder)"
	@echo "drift         run freshness + router-drift -> reports/DRIFT_REPORT.md"
	@echo "validate      validate a plan:  make validate PLAN=eval/plans/valid_174_stream.plan.yaml"
	@echo "solve         build a reference plan:  make solve TAKEN='CMPUT 174,MATH 125'"

engine-test:
	$(PYTHON) -m pytest tests/test_planner_expr.py tests/test_planner_matching.py \
	    tests/test_planner_validate.py tests/test_planner_plans.py tests/test_planner_solve.py \
	    tests/test_planner_oracle.py -q

test:
	$(PYTHON) -m pytest -q

snapshot:
	$(PYTHON) eval/snapshots/build_snapshot.py

snapshot2:
	$(PYTHON) eval/snapshots/make_synthetic_snapshot.py

rag-build:
	$(PYTHON) -m rag.build

queries:
	$(PYTHON) eval/queries/build_queries.py

# Real eval (needs DEEPSEEK_API_KEY). Falls back to the offline stub if unset.
eval:
	$(PYTHON) -m eval.metrics.harness

eval-stub:
	$(PYTHON) -m eval.metrics.harness --provider stub --embedder hashing

drift:
	$(PYTHON) -m eval.metrics.drift

PLAN ?= eval/plans/valid_174_stream.plan.yaml
validate:
	$(PYTHON) -m planner validate $(PLAN)

TAKEN ?=
solve:
	$(PYTHON) -m planner solve --taken "$(TAKEN)"

clean:
	rm -rf .pytest_cache **/__pycache__
