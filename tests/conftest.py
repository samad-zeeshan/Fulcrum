from pathlib import Path

import pytest

from planner import Gold, Snapshot

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "eval" / "snapshots" / "2026-06-28" / "offerings.json"
PLANS_DIR = ROOT / "eval" / "plans"

@pytest.fixture(scope="session")
def gold() -> Gold:
    return Gold.load()

@pytest.fixture(scope="session")
def snap() -> Snapshot:
    return Snapshot.load(SNAPSHOT)
