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

def _leaf_course(code: str, ctx: EvalContext) -> bool:
    if ctx.available(code):
        return True

    if ctx.is_program_course(code):
        return False
    return not ctx.cfg.enforce_external_prereqs

def evaluate(expr, ctx: EvalContext) -> bool:
    if expr is None:
        return True
    if isinstance(expr, str):
        return _leaf_course(expr, ctx)
    if isinstance(expr, dict):
        if "one_of" in expr:
            return any(evaluate(e, ctx) for e in expr["one_of"])
        if "all_of" in expr:
            return all(evaluate(e, ctx) for e in expr["all_of"])
        if "hs" in expr:
            return bool(ctx.cfg.hs_satisfied_by_admission)
        if "pattern" in expr:
            return ctx.available_matching(expr["pattern"])
        raise ValueError(f"unrecognised prereq expression: {expr!r}")
    raise TypeError(f"prereq expression must be str/dict/None, got {type(expr)}")

def referenced_courses(expr) -> set[str]:
    out: set[str] = set()
    if isinstance(expr, str):
        out.add(expr)
    elif isinstance(expr, dict):
        for key in ("one_of", "all_of"):
            for e in expr.get(key, []):
                out |= referenced_courses(e)
    return out
