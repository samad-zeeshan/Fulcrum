"""
Parses a section's schedule cell into structured meetings.

Handles single-letter day codes (M T W R F, R is Thursday), date ranges and
start/end times, and keeps unparseable text as a schedule note.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# UAlberta uses single-letter day codes; R is Thursday and U is Sunday.
DAY_NAMES = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "R": "Thursday",
    "F": "Friday",
    "S": "Saturday",
    "U": "Sunday",
}

KNOWN_DAY_CODES = set("MTWRF")

_DATE_RE = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2})\s*(?:-\s*(\d{4}-\d{2}-\d{2})\s*)?(?:\(([^)]*)\))?\s*$"
)

_TIME_RE = re.compile(r"^\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*$")

@dataclass
class Meeting:
    date_start: str | None = None
    date_end: str | None = None
    days: list[str] = field(default_factory=list)
    time_start: str | None = None
    time_end: str | None = None

    def as_dict(self) -> dict:
        return {
            "date_start": self.date_start,
            "date_end": self.date_end,
            "days": list(self.days),
            "time_start": self.time_start,
            "time_end": self.time_end,
        }

    def key(self) -> tuple:
        return (
            self.date_start,
            self.date_end,
            tuple(self.days),
            self.time_start,
            self.time_end,
        )

# Split a day string into letters, returning any code we do not recognise.
def expand_day_codes(raw: str) -> tuple[list[str], list[str]]:
    codes: list[str] = []
    unknown: list[str] = []
    for ch in raw.strip():
        if ch.isspace() or ch == ",":
            continue
        codes.append(ch)
        if ch not in KNOWN_DAY_CODES:
            unknown.append(ch)
    return codes, unknown

def parse_date_col(text: str) -> tuple[Meeting | None, list[str]]:
    m = _DATE_RE.match(text)
    if not m:
        return None, []
    days_raw = m.group(3) or ""
    days, unknown = expand_day_codes(days_raw)

    date_end = m.group(2) or m.group(1)
    return Meeting(date_start=m.group(1), date_end=date_end, days=days), unknown

def parse_time_col(text: str) -> tuple[str, str] | None:
    m = _TIME_RE.match(text)
    if not m:
        return None
    return _pad(m.group(1)), _pad(m.group(2))

def _pad(t: str) -> str:
    h, mnt = t.split(":")
    return f"{int(h):02d}:{mnt}"

@dataclass
class CellResult:
    meetings: list[Meeting]
    schedule_note: str | None
    flags: list[str]

# Walk the date/time columns in order, pairing each date with the time that
# follows it into one meeting. Anything that does not pair becomes a note.
def parse_class_times(cols: list[tuple[str, str]], raw_cell_text: str) -> CellResult:
    meetings: list[Meeting] = []
    flags: list[str] = []
    note_parts: list[str] = []

    i = 0
    n = len(cols)
    while i < n:
        kind, text = cols[i]
        if kind == "date":
            mtg, unknown = parse_date_col(text)
            if mtg is None:
                flags.append(f"unparseable-date-col:{text!r}")
                note_parts.append(text.strip())
                i += 1
                continue
            for u in unknown:
                flags.append(f"unknown-day-code:{u!r} in {text!r}")

            if i + 1 < n and cols[i + 1][0] == "time":
                tr = parse_time_col(cols[i + 1][1])
                if tr is None:
                    flags.append(f"unparseable-time-col:{cols[i + 1][1]!r}")
                    note_parts.append(text.strip())
                else:
                    mtg.time_start, mtg.time_end = tr
                    meetings.append(mtg)
                i += 2
            else:

                note_parts.append(text.strip())
                i += 1
        elif kind == "time":

            flags.append(f"orphan-time-col:{text!r}")
            note_parts.append(text.strip())
            i += 1
        else:
            flags.append(f"unknown-col-kind:{kind!r}")
            i += 1

    # Drop duplicate meeting rows that repeat the same date, days and time.
    seen: set[tuple] = set()
    deduped: list[Meeting] = []
    for mtg in meetings:
        k = mtg.key()
        if k in seen:
            continue
        seen.add(k)
        deduped.append(mtg)

    # If nothing parsed, keep the raw text so the section is not silently empty.
    schedule_note: str | None = None
    if not deduped:

        schedule_note = " | ".join(p for p in note_parts if p) or (
            raw_cell_text.strip() or "No scheduled meeting times"
        )
    elif note_parts:

        schedule_note = " | ".join(p for p in note_parts if p) or None

    return CellResult(meetings=deduped, schedule_note=schedule_note, flags=flags)
