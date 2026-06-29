"""
CAG path: answer rules questions from the cached rules slice, citing clause ids.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from llm.provider import LLMProvider, LLMResponse, StubProvider
from planner.gold import Gold

from .rules_slice import RulesSlice, build_rules_slice

# Appended after the rules slice: answer only from those rules and cite a
# [clause-id] for every claim.
SYSTEM_SUFFIX = (
    "\n\nYou are a University of Alberta Computing Science requirements assistant. "
    "Answer ONLY from the requirement rules above. Cite the [clause-id] (e.g. "
    "[group:senior_required], [note:note1_275_blocks_201], [prereq:CMPUT 204]) for "
    "every claim. If a plan-validity question is asked, answer VALID or INVALID and "
    "cite the binding clause. Be concise."
)

CLAUSE_RE = re.compile(r"\[(group|note|prereq|exclusion):?([^\]]*)\]")

@dataclass
class CagContext:
    slice: RulesSlice
    system: str

    @classmethod
    def from_gold(cls, gold: Gold) -> "CagContext":
        rs = build_rules_slice(gold)
        return cls(slice=rs, system=rs.text + SYSTEM_SUFFIX)

@dataclass
class CagAnswer:
    query: str
    text: str
    cited_clauses: list[str]
    response: LLMResponse | None = None
    extra: dict = field(default_factory=dict)

    @property
    def cost_usd(self) -> float:
        return self.response.cost_usd if self.response else 0.0

    @property
    def latency_s(self) -> float:
        return self.response.latency_s if self.response else 0.0

    @property
    def cache_hit_rate(self) -> float:
        return self.response.usage.cache_hit_rate if self.response else 0.0

def _extract_clauses(text: str) -> list[str]:
    out = []
    for kind, body in CLAUSE_RE.findall(text):
        out.append(f"{kind}:{body}".rstrip(":"))
    return list(dict.fromkeys(out))

def answer_rules_query(query: str, ctx: CagContext,
                       provider: LLMProvider | None = None) -> CagAnswer:
    provider = provider or StubProvider()
    resp = provider.complete(ctx.system, query)
    return CagAnswer(query=query, text=resp.text,
                     cited_clauses=_extract_clauses(resp.text), response=resp)

# Prime DeepSeek's prompt cache with the rules prefix before metrics are taken.
def warm_cache(ctx: CagContext, provider: LLMProvider, n: int = 3) -> list[LLMResponse]:
    return [provider.complete(ctx.system, "Reply READY.") for _ in range(n)]
