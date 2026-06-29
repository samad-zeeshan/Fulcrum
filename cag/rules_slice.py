from __future__ import annotations

from dataclasses import dataclass

from planner.gold import Gold

def _fmt_expr(e) -> str:
    if e is None:
        return "none"
    if isinstance(e, str):
        return e
    if "one_of" in e:
        return "one of (" + ", ".join(_fmt_expr(x) for x in e["one_of"]) + ")"
    if "all_of" in e:
        return " and ".join(_fmt_expr(x) for x in e["all_of"])
    if "hs" in e:
        return f"high-school {e['hs']}"
    if "pattern" in e:
        p = e["pattern"]
        bits = []
        if "subject" in p:
            bits.append(p["subject"])
        if "level_in" in p:
            bits.append("/".join(f"{l}-level" for l in p["level_in"]))
        if "level_gte" in p:
            bits.append(f">={p['level_gte']}-level")
        return "any " + " ".join(bits) + " course"
    return str(e)

def _group_clause(g) -> str:
    if g.type == "all_of":
        members = "; ".join(_fmt_expr(m) for m in g.members)
        return f"[group:{g.id}] ALL of: {members}."
    if g.type == "units_from":
        return f"[group:{g.id}] {g.units_required} units from: {', '.join(g.options)}."
    if g.type == "units_from_pattern":
        return f"[group:{g.id}] {g.units_required} units from {_fmt_expr({'pattern': g.pattern})}."
    return f"[group:{g.id}] {g.type}"

@dataclass
class RulesSlice:
    text: str
    clause_ids: set[str]

    def __len__(self) -> int:
        return len(self.text)

def build_rules_slice(gold: Gold) -> RulesSlice:
    p = gold.program
    lines: list[str] = []
    lines.append(f"PROGRAM: {p.get('name')} (catalog year {p.get('catalog_year')}), "
                 f"{p.get('total_units')} units of major requirements.")
    lines.append("Scope: major requirements + prerequisite feasibility (not the full BSc).")
    lines.append("")
    lines.append("REQUIREMENT GROUPS (each course credits to at most one group):")
    for g in gold.groups:
        lines.append("  " + _group_clause(g))

    lines.append("")
    lines.append("CONDITIONALS:")
    for c in gold.conditionals:
        eff = []
        for e in c.effects:
            if "ineligible" in e:
                eff.append(f"{e['ineligible']} becomes ineligible")
            if "modify_group" in e:
                mg = e["modify_group"]
                eff.append(f"group {mg['id']} -> options {mg.get('set_options')} "
                           f"plus {_fmt_expr({'pattern': mg['add_pattern']})}" if mg.get("add_pattern")
                           else f"group {mg['id']} -> options {mg.get('set_options')}")
        lines.append(f"  [note:{c.id}] when {c.when.get('taken')} is taken: " + "; ".join(eff) + ".")

    lines.append("")
    lines.append("CREDIT EXCLUSIONS (at most one course per set earns credit):")
    for x in gold.credit_exclusions:
        lines.append(f"  [exclusion] {', '.join(x.courses)} — \"{x.source}\"")

    lines.append("")
    lines.append("PREREQUISITES (course: structured prereq — verbatim calendar source):")
    for course in sorted(gold.prerequisites):
        e = gold.prerequisites[course]
        pr = _fmt_expr(e.prereq)
        line = f"  [prereq:{course}] {pr}"
        if e.coreq is not None:
            line += f"; corequisite: {_fmt_expr(e.coreq)}"
        if e.source:
            line += f"  (source: \"{e.source}\")"
        lines.append(line)

    text = "\n".join(lines)
    clause_ids = {f"group:{g.id}" for g in gold.groups}
    clause_ids |= {f"note:{c.id}" for c in gold.conditionals}
    clause_ids |= {f"prereq:{c}" for c in gold.prerequisites}
    return RulesSlice(text=text, clause_ids=clause_ids)
