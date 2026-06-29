from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from .config import EngineConfig
from .gold import Gold
from .requirements import Requirements, Slot, units_of
from .snapshot import Snapshot

def _u10(x: float) -> int:
    return int(round(x * 10))

@dataclass
class SlotResult:
    slot_id: str
    group_id: str
    label: str
    required_units: float
    earned_units: float
    shortfall_units: float
    assigned: list[str]

@dataclass
class MatchResult:
    satisfied: bool
    slots: list[SlotResult]

    def unmet(self) -> list[SlotResult]:
        return [s for s in self.slots if s.shortfall_units > 1e-9]

def match_requirements(
    creditable: set[str],
    reqs: Requirements,
    gold: Gold,
    snap: Snapshot,
    cfg: EngineConfig,
) -> MatchResult:
    courses = sorted(creditable)
    slots = reqs.slots
    model = cp_model.CpModel()

    x: dict[tuple[str, str], cp_model.IntVar] = {}
    for c in courses:
        for s in slots:
            if s.eligible(c, snap):
                x[(c, s.id)] = model.NewBoolVar(f"x[{c}|{s.id}]")

    for c in courses:
        vars_c = [x[(c, s.id)] for s in slots if (c, s.id) in x]
        if vars_c:
            model.Add(sum(vars_c) <= 1)

    short: dict[str, cp_model.IntVar] = {}
    for s in slots:
        members = [x[(c, s.id)] for c in courses if (c, s.id) in x]
        if s.kind == "exactly_one":
            filled = sum(members) if members else 0
            if members:
                model.Add(sum(members) <= 1)
            sh = model.NewIntVar(0, 1, f"short[{s.id}]")
            model.Add(sh >= 1 - filled)
            short[s.id] = sh
        else:
            req10 = _u10(s.units_required)
            earned = sum(_u10(units_of(gold, snap, c)) * x[(c, s.id)] for c in courses if (c, s.id) in x)
            sh = model.NewIntVar(0, req10, f"short[{s.id}]")
            model.Add(sh >= req10 - earned)
            short[s.id] = sh

    model.Minimize(sum(short.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.solver_max_seconds
    solver.parameters.random_seed = cfg.random_seed
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"matching solver returned status {solver.StatusName(status)}")

    results: list[SlotResult] = []
    for s in slots:
        assigned = [c for c in courses if (c, s.id) in x and solver.Value(x[(c, s.id)]) == 1]
        earned_units = sum(units_of(gold, snap, c) for c in assigned)
        sh_units = solver.Value(short[s.id]) / 10.0 if s.kind == "units" else float(solver.Value(short[s.id]))
        results.append(SlotResult(
            slot_id=s.id, group_id=s.group_id, label=s.label,
            required_units=(s.units_required if s.kind == "units" else 1.0),
            earned_units=earned_units, shortfall_units=sh_units, assigned=assigned,
        ))

    satisfied = solver.ObjectiveValue() < 1e-6
    return MatchResult(satisfied=satisfied, slots=results)
