"""
Validates a degree plan against the gold requirements and a frozen snapshot.

Runs exactly five checks: duplicate credit, credit-exclusion, term availability,
prereq/coreq ordering, and the global requirement matching and collecting every
failure instead of stopping at the first.
"""


from __future__ import annotations
from dataclasses import dataclass, field
from .config import DEFAULT_CONFIG, EngineConfig
from .expr import EvalContext, evaluate
from .gold import DEFAULT_GOLD, Gold
from .matching import MatchResult, match_requirements
from .plan import Plan
from .requirements import build_requirements, program_courses
from .snapshot import Snapshot, season_of

@dataclass
class Failure:
    code: str
    detail: str
    courses: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        tail = f" [{', '.join(self.courses)}]" if self.courses else ""
        return f"{self.code}: {self.detail}{tail}"

@dataclass
class ValidationResult:
    valid: bool
    failures: list[Failure]
    notes: list[str] = field(default_factory=list)
    applied_conditionals: list[str] = field(default_factory=list)
    match: MatchResult | None = None

    def __bool__(self) -> bool:
        return self.valid

def _eval_context(available: set[str], prog: set[str], snap: Snapshot, cfg: EngineConfig) -> EvalContext:
    return EvalContext(
        available=lambda c: c in available,
        is_program_course=lambda c: c in prog,
        available_matching=lambda pat: any(snap.matches_pattern(c, pat) for c in available),
        cfg=cfg,
    )

def validate(
    plan: Plan,
    gold: Gold | None = None,
    snap: Snapshot | None = None,
    cfg: EngineConfig = DEFAULT_CONFIG,
) -> ValidationResult:
    gold = gold or Gold.load(DEFAULT_GOLD)
    # Validation must be reproducible so it reads only a frozen snapshot and never the live catalogue.
    if snap is None: 
        raise ValueError("validate() requires a frozen offerings snapshot (no live calls)")

    failures: list[Failure] = []
    notes: list[str] = []
    prog = program_courses(gold, snap)

    seen: set[str] = set()
    dupes: set[str] = set()
    for c in plan.all_courses():
        if c in seen:
            dupes.add(c)
        seen.add(c)
    if dupes:
        failures.append(Failure("duplicate_course",
                                "course credited more than once", sorted(dupes)))
    earned = set(seen)

    reqs = build_requirements(gold, earned)
    if reqs.applied_conditionals:
        notes.append("conditionals applied: " + ", ".join(reqs.applied_conditionals))
    if reqs.ineligible & earned:
        bad = sorted(reqs.ineligible & earned)
        failures.append(Failure("ineligible_course",
                                "course is ineligible under an active conditional and earns no credit",
                                bad))

    for excl in gold.credit_exclusions:
        clash = sorted(set(excl.courses) & earned)
        if len(clash) > 1:
            failures.append(Failure("credit_exclusion",
                                    f"at most one of {excl.courses} may earn credit", clash))



    # Exact-term offering if the snapshot knows that term otherwise fall back to
    # season recurrence (e.g. "offered every Fall") for terms past the snapshot horizon.
    for t in plan.terms:
        for c in t.courses:
            if c not in snap.courses:
                continue
            if t.term in snap.term_index:
                offered = snap.is_offered_in_term(c, t.term)
            else:
                offered = snap.is_offered_in_season(c, season_of(t.term))
            if not offered:
                terms = ", ".join(snap.courses[c].terms) or "(no terms in snapshot)"
                failures.append(Failure("not_offered",
                                        f"{c} is not offered in {t.term}; offered: {terms}", [c]))


    # Prereqs must be met by a STRICTLY earlier term and coreqs may be met in the
    # same term so they get the wider `same_or_before` set.
    for i, t in enumerate(plan.terms):
        before = set(plan.taken) | {c for tt in plan.terms[:i] for c in tt.courses}
        same_or_before = before | set(t.courses)
        for c in t.courses:
            entry = gold.prerequisites.get(c)
            # No verified prereq entry: the full parser is deferred so flag
            # program courses as unverified rather than passing them silently.
            if entry is None:
                if c in prog and c not in gold.named_courses():
                    notes.append(f"{c}: prereq unverified (no DAG entry; Phase B parser)")
                continue
            if entry.prereq is not None:
                ctx = _eval_context(before, prog, snap, cfg)
                if not evaluate(entry.prereq, ctx):
                    failures.append(Failure("prereq_unsatisfied",
                                            f"{c} prereq not met before {t.term}: \"{entry.source}\"", [c]))
            if entry.coreq is not None:
                ctx = _eval_context(same_or_before, prog, snap, cfg)
                if not evaluate(entry.coreq, ctx):
                    failures.append(Failure("coreq_unsatisfied",
                                            f"{c} coreq not met by {t.term}: \"{entry.coreq_source}\"", [c]))

    creditable = earned - reqs.ineligible
    match = match_requirements(creditable, reqs, gold, snap, cfg)
    if not match.satisfied:
        for sr in match.unmet(): # "pick exactly one" slots get a named-requirement message
            if sr.required_units == 1.0 and sr.shortfall_units >= 1.0 and sr.label and "u from" not in sr.label and "u matching" not in sr.label:
                detail = f"unmet requirement '{sr.group_id}': need {sr.label}"
            else:
                detail = (f"unmet requirement '{sr.group_id}' ({sr.label}): "
                          f"have {sr.earned_units:g}u, short {sr.shortfall_units:g}u")
            failures.append(Failure("requirement_shortfall", detail, sr.assigned))

    return ValidationResult(
        valid=len(failures) == 0,
        failures=failures,
        notes=notes,
        applied_conditionals=reqs.applied_conditionals,
        match=match,
    )
