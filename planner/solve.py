from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from .config import DEFAULT_CONFIG, EngineConfig
from .gold import DEFAULT_GOLD, Gold
from .plan import Plan, PlanTerm
from .requirements import build_requirements, program_courses, units_of
from .snapshot import Snapshot, season_of

@dataclass
class SolveResult:
    found: bool
    plan: Plan | None
    terms_to_graduate: int | None
    chosen: list[str] = field(default_factory=list)
    status: str = ""

    def __bool__(self) -> bool:
        return self.found

def _u10(x: float) -> int:
    return int(round(x * 10))

def _future_terms(snap: Snapshot, cfg: EngineConfig) -> list[tuple[str, str]]:
    seasons = list(cfg.planning_seasons)
    out: list[tuple[str, str]] = []
    while len(out) < cfg.horizon_terms:
        season = seasons[len(out) % len(seasons)]
        out.append((f"Term {len(out) + 1} ({season})", season))
    return out

def solve(
    taken: list[str] | set[str] | None = None,
    gold: Gold | None = None,
    snap: Snapshot | None = None,
    cfg: EngineConfig = DEFAULT_CONFIG,
) -> SolveResult:
    gold = gold or Gold.load(DEFAULT_GOLD)
    if snap is None:
        raise ValueError("solve() requires a frozen offerings snapshot (no live calls)")
    taken = set(taken or [])

    prog = program_courses(gold, snap)
    reqs = build_requirements(gold, taken)
    ineligible = reqs.ineligible
    slots = reqs.slots

    future = _future_terms(snap, cfg)
    H = len(future)

    universe = gold.eval_scope() if cfg.restrict_candidates_to_scope else prog
    candidates = sorted((universe - taken) - ineligible)

    season_slots: dict[str, list[int]] = {}
    for k, (_, season) in enumerate(future):
        season_slots.setdefault(season, []).append(k)
    schedulable = [c for c in candidates
                   if any(snap.is_offered_in_season(c, s) for s in season_slots)]

    model = cp_model.CpModel()

    take = {c: model.NewBoolVar(f"take[{c}]") for c in schedulable}
    place = {}
    term = {}
    for c in schedulable:
        valid_k = [k for k, (_, season) in enumerate(future) if snap.is_offered_in_season(c, season)]
        for k in valid_k:
            place[(c, k)] = model.NewBoolVar(f"place[{c}|{k}]")
        model.Add(sum(place[(c, k)] for k in valid_k) == take[c])
        tv = model.NewIntVar(0, H - 1, f"term[{c}]")
        model.Add(tv == sum(k * place[(c, k)] for k in valid_k))
        term[c] = tv

    creditable = sorted((taken | set(schedulable)))
    assign = {}
    for c in creditable:
        for s in slots:
            if s.eligible(c, snap):
                assign[(c, s.id)] = model.NewBoolVar(f"a[{c}|{s.id}]")
    for c in creditable:
        a_c = [assign[(c, s.id)] for s in slots if (c, s.id) in assign]
        if a_c:
            model.Add(sum(a_c) <= 1)

        if c in take:
            for s in slots:
                if (c, s.id) in assign:
                    model.Add(assign[(c, s.id)] <= take[c])
    for s in slots:
        members = [assign[(c, s.id)] for c in creditable if (c, s.id) in assign]
        if s.kind == "exactly_one":
            model.Add(sum(members) == 1)
        else:
            req10 = _u10(s.units_required)
            model.Add(sum(_u10(units_of(gold, snap, c)) * assign[(c, s.id)]
                          for c in creditable if (c, s.id) in assign) >= req10)

    for excl in gold.credit_exclusions:
        members = [take[c] for c in excl.courses if c in take]
        taken_hit = any(c in taken for c in excl.courses)
        if taken_hit:
            for v in members:
                model.Add(v == 0)
        elif len(members) > 1:
            model.Add(sum(members) <= 1)

    cap10 = _u10(cfg.max_units_per_term)
    for k in range(H):
        load = [_u10(units_of(gold, snap, c)) * place[(c, k)]
                for c in schedulable if (c, k) in place]
        if load:
            model.Add(sum(load) <= cap10)

    TRUE = model.NewConstant(1)
    FALSE = model.NewConstant(0)

    def leaf_literal(course_code: str, tc, strict: bool):
        if course_code in taken:
            return TRUE
        if course_code in take:
            b = model.NewBoolVar(f"avail[{course_code}<{tc.Name()}|{int(strict)}]")
            model.Add(b <= take[course_code])
            tp = term[course_code]
            if strict:
                model.Add(tp + 1 <= tc).OnlyEnforceIf(b)
            else:
                model.Add(tp <= tc).OnlyEnforceIf(b)
            return b

        return FALSE if cfg.enforce_external_prereqs else TRUE

    def expr_literal(expr, tc, strict: bool):
        if expr is None:
            return TRUE
        if isinstance(expr, str):
            return leaf_literal(expr, tc, strict)
        if "hs" in expr:
            return TRUE if cfg.hs_satisfied_by_admission else FALSE
        if "pattern" in expr:
            pat = expr["pattern"]
            lits = [leaf_literal(c, tc, strict) for c in (set(schedulable) | taken)
                    if snap.matches_pattern(c, pat)]
            return _or(lits)
        if "one_of" in expr:
            return _or([expr_literal(e, tc, strict) for e in expr["one_of"]])
        if "all_of" in expr:
            return _and([expr_literal(e, tc, strict) for e in expr["all_of"]])
        raise ValueError(f"bad expr {expr!r}")

    def _or(lits):
        lits = list(lits)
        if not lits:
            return FALSE
        if TRUE in lits:
            return TRUE
        lits = [l for l in lits if l is not FALSE]
        if not lits:
            return FALSE
        if len(lits) == 1:
            return lits[0]
        r = model.NewBoolVar("or")
        model.AddBoolOr(lits).OnlyEnforceIf(r)
        for l in lits:
            model.AddImplication(l, r)
        return r

    def _and(lits):
        lits = list(lits)
        if FALSE in lits:
            return FALSE
        lits = [l for l in lits if l is not TRUE]
        if not lits:
            return TRUE
        if len(lits) == 1:
            return lits[0]
        r = model.NewBoolVar("and")
        for l in lits:
            model.AddImplication(r, l)
        model.AddBoolOr([l.Not() for l in lits] + [r])
        return r

    def enforce(course, root):
        if root is TRUE:
            return
        if root is FALSE:
            model.Add(take[course] == 0)
        else:
            model.AddImplication(take[course], root)

    for c in schedulable:
        entry = gold.prerequisites.get(c)
        if entry is None:
            continue
        tc = term[c]
        if entry.prereq is not None:
            enforce(c, expr_literal(entry.prereq, tc, strict=True))
        if entry.coreq is not None:
            enforce(c, expr_literal(entry.coreq, tc, strict=False))

    makespan = model.NewIntVar(0, H - 1, "makespan")
    for c in schedulable:
        model.Add(makespan >= term[c]).OnlyEnforceIf(take[c])
    total_take = sum(take.values())
    model.Minimize(makespan * 1000 + total_take)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.solver_max_seconds
    solver.parameters.random_seed = cfg.random_seed
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveResult(found=False, plan=None, terms_to_graduate=None,
                           status=solver.StatusName(status))

    chosen = [c for c in schedulable if solver.Value(take[c]) == 1]
    used = solver.Value(makespan) + 1
    plan_terms: list[PlanTerm] = []
    for k in range(used):
        label = future[k][0]
        courses_k = sorted(c for c in chosen if (c, k) in place and solver.Value(place[(c, k)]) == 1)
        if courses_k:
            plan_terms.append(PlanTerm(term=label, courses=courses_k))
    plan = Plan(plan_id="reference_plan", terms=plan_terms, taken=sorted(taken),
                description=f"solve() reference plan ({used} terms)")
    return SolveResult(found=True, plan=plan, terms_to_graduate=used,
                       chosen=sorted(chosen), status=solver.StatusName(status))
