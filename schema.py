from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class Section:
    term: str
    term_code: str | None
    component: str
    section: str
    class_id: str | None
    capacity: int | None
    meetings: list[dict] = field(default_factory=list)
    schedule_note: str | None = None
    instructor: None = None
    location: None = None

    def as_dict(self) -> dict:
        return {
            "term": self.term,
            "term_code": self.term_code,
            "component": self.component,
            "section": self.section,
            "class_id": self.class_id,
            "capacity": self.capacity,
            "meetings": self.meetings,
            "schedule_note": self.schedule_note,
            "instructor": self.instructor,
            "location": self.location,
        }

@dataclass
class Course:
    course_id: str
    subject: str
    catalog_number: str
    title: str | None
    credits: float | None
    faculty: str | None
    career: str | None
    units_string: str | None
    description_raw: str | None
    prereq_raw: str | None
    coreq_raw: str | None
    credit_exclusion_raw: str | None
    terms_offered: list[str]
    source_url: str
    fetched_at: str | None
    sections: list[dict] = field(default_factory=list)

    note_raw: str | None = None
    term_notes: dict | None = None
    meta_sections: int | None = None
    meta_sections_online: int | None = None

    def as_dict(self) -> dict:
        d = {
            "course_id": self.course_id,
            "subject": self.subject,
            "catalog_number": self.catalog_number,
            "title": self.title,
            "credits": self.credits,
            "faculty": self.faculty,
            "career": self.career,
            "units_string": self.units_string,
            "description_raw": self.description_raw,
            "prereq_raw": self.prereq_raw,
            "coreq_raw": self.coreq_raw,
            "credit_exclusion_raw": self.credit_exclusion_raw,
            "terms_offered": self.terms_offered,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at,
            "sections": self.sections,
        }
        if self.note_raw is not None:
            d["note_raw"] = self.note_raw
        if self.term_notes:
            d["term_notes"] = self.term_notes
        d["meta_sections"] = self.meta_sections
        d["meta_sections_online"] = self.meta_sections_online
        return d

@dataclass
class RequirementBlock:
    heading: str
    rule_text_raw: str | None
    courses: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "heading": self.heading,
            "rule_text_raw": self.rule_text_raw,
            "courses": list(self.courses),
        }

@dataclass
class Program:
    poid: str
    program_name: str | None
    degree: str | None
    catoid: str
    tier: str
    requirement_blocks_raw: list[dict]
    source_url: str
    fetched_at: str | None
    parse_confidence: str

    def as_dict(self) -> dict:
        return {
            "poid": self.poid,
            "program_name": self.program_name,
            "degree": self.degree,
            "catoid": self.catoid,
            "tier": self.tier,
            "requirement_blocks_raw": self.requirement_blocks_raw,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at,
            "parse_confidence": self.parse_confidence,
        }
