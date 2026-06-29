from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class EngineConfig:

    enforce_external_prereqs: bool = False

    hs_satisfied_by_admission: bool = True

    max_units_per_term: float = 15.0
    horizon_terms: int = 12

    restrict_candidates_to_scope: bool = False

    planning_seasons: tuple[str, ...] = ("Fall", "Winter")

    solver_max_seconds: float = 30.0
    random_seed: int = 0

DEFAULT_CONFIG = EngineConfig()
