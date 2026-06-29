from __future__ import annotations

from dataclasses import dataclass, field

from .gold import Gold, Group
from .snapshot import Snapshot

@dataclass
class Slot:
    id: str
    group_id: str
    kind: str
    units_required: float
    options: frozenset[str] = frozenset()
    pattern: dict | None = None
    label: str = ""

    def eligible(self, course: str, snap: Snapshot) -> bool:
        if course in self.options:
            return True
        if self.pattern is not None and snap.matches_pattern(course, self.pattern):
            return True
        return False

def _slots_for_group(g: Group) -> list[Slot]:
    if g.type == "all_of":
        slots: list[Slot] = []
        for i, member in enumerate(g.members):
            if isinstance(member, str):
                opts, label = frozenset({member}), member
            elif isinstance(member, dict) and "one_of" in member:
                opts = frozenset(member["one_of"])
                label = "one of " + ", ".join(sorted(opts))
            else:
                raise ValueError(f"unsupported all_of member in {g.id}: {member!r}")
            slots.append(Slot(
                id=f"{g.id}[{i}]", group_id=g.id, kind="exactly_one",
                units_required=1, options=opts, label=label,
            ))
        return slots
    if g.type == "units_from":
        return [Slot(
            id=g.id, group_id=g.id, kind="units", units_required=g.units_required,
            options=frozenset(g.options),
            label=f"{g.units_required}u from {', '.join(g.options)}",
        )]
    if g.type == "units_from_pattern":
        return [Slot(
            id=g.id, group_id=g.id, kind="units", units_required=g.units_required,
            pattern=g.pattern,
            label=f"{g.units_required}u matching {g.pattern}",
        )]
    raise ValueError(f"unknown group type: {g.type}")

@dataclass
class Requirements:
    slots: list[Slot]
    ineligible: frozenset[str]
    applied_conditionals: list[str] = field(default_factory=list)

def build_requirements(gold: Gold, taken_or_earned: set[str]) -> Requirements:
    base: dict[str, list[Slot]] = {g.id: _slots_for_group(g) for g in gold.groups}
    ineligible: set[str] = set()
    applied: list[str] = []

    for cond in gold.conditionals:
        trigger = cond.when.get("taken")
        if trigger and trigger in taken_or_earned:
            applied.append(cond.id)
            for effect in cond.effects:
                if "ineligible" in effect:
                    ineligible.add(effect["ineligible"])
                if "modify_group" in effect:
                    mg = effect["modify_group"]
                    gid = mg["id"]
                    if gid not in base or len(base[gid]) != 1:
                        raise ValueError(f"modify_group target {gid} is not a single-slot group")
                    slot = base[gid][0]
                    new_opts = frozenset(mg.get("set_options", slot.options))
                    new_pattern = mg.get("add_pattern", slot.pattern)
                    base[gid] = [Slot(
                        id=slot.id, group_id=slot.group_id, kind=slot.kind,
                        units_required=slot.units_required, options=new_opts,
                        pattern=new_pattern,
                        label=f"{slot.units_required}u from {sorted(new_opts)} or {new_pattern}",
                    )]

    slots = [s for group_slots in base.values() for s in group_slots]
    return Requirements(slots=slots, ineligible=frozenset(ineligible), applied_conditionals=applied)

def program_courses(gold: Gold, snap: Snapshot) -> set[str]:
    out: set[str] = set(gold.named_courses())
    for g in gold.groups:
        out.update(g.options)
        for member in g.members:
            if isinstance(member, str):
                out.add(member)
            elif isinstance(member, dict) and "one_of" in member:
                out.update(member["one_of"])
        if g.pattern:
            out |= snap.courses_matching(g.pattern)
    return out

def units_of(gold: Gold, snap: Snapshot, course: str) -> float:
    if course in gold.courses and gold.courses[course].get("units") is not None:
        return float(gold.courses[course]["units"])
    return snap.units_of(course)
