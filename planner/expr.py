"""
Evaluates a prereq or coreq expression against the courses a student has.

Expressions are nested str/dict nodes: a course code, one_of (OR), all_of (AND),
a pattern wildcard, or hs for a high school requirement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .config import EngineConfig

@dataclass
class EvalContext:

    available: Callable[[str], bool]

    is_program_course: Callable[[str], bool]

    available_matching: Callable[[dict], bool]
    cfg: EngineConfig

# A single course code. Satisfied if the student has it. A program course they
# have not taken fails; an outside course passes unless the config enforces
# external prereqs.
def _leaf_course(code: str, ctx: EvalContext) -> bool:
    if ctx.available(code):
        return True

    if ctx.is_program_course(code):
        return False
    return not ctx.cfg.enforce_external_prereqs

def evaluate(expr, ctx: EvalContext) -> bool:
    # No prereq means there is nothing to satisfy.
    if expr is None:
        return True
    if isinstance(expr, str):
        return _leaf_course(expr, ctx)
    if isinstance(expr, dict):
        # one_of is OR and all_of is AND. This is what makes prereq checking
        # disjunction aware instead of treating every code as mandatory.
        if "one_of" in expr:
            return any(evaluate(e, ctx) for e in expr["one_of"])
        if "all_of" in expr:
            return all(evaluate(e, ctx) for e in expr["all_of"])
        # hs is a high school requirement, taken as met on admission.
        if "hs" in expr:
            return bool(ctx.cfg.hs_satisfied_by_admission)
        # pattern is a wildcard like any 300-level CMPUT.
        if "pattern" in expr:
            return ctx.available_matching(expr["pattern"])
        raise ValueError(f"unrecognised prereq expression: {expr!r}")
    raise TypeError(f"prereq expression must be str/dict/None, got {type(expr)}")

# Collect the explicit course codes in an expression. Patterns and hs have no
# fixed code so they are skipped.
def referenced_courses(expr) -> set[str]:
    out: set[str] = set()
    if isinstance(expr, str):
        out.add(expr)
    elif isinstance(expr, dict):
        for key in ("one_of", "all_of"):
            for e in expr.get(key, []):
                out |= referenced_courses(e)
    return out
