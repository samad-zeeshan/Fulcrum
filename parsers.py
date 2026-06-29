"""
Pure HTML to structured records, with no network or state.

Courses come from ua__cat_* meta tags plus the section tables; programs come
from Acalog requirement blocks. Requirement strings are captured verbatim with
no boolean prereq logic.
"""

from __future__ import annotations

import re

from selectolax.parser import HTMLParser, Node

import config
import daycodes
from schema import Course, Program, RequirementBlock, Section

NBSP = " "

def _clean(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text.replace(NBSP, " ")).strip()

# The ua__cat_* meta tags in the page head are the primary structured source.
def _metas(tree: HTMLParser) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in tree.css("meta[name^='ua__cat']"):
        name = m.attributes.get("name")
        content = m.attributes.get("content")
        if name is not None and content is not None:
            out[name] = content
    return out

def _to_float(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None

def _to_int(s: str | None) -> int | None:
    if s is None:
        return None
    try:
        return int(s)
    except ValueError:
        return None

# Lead-in phrases that mark each requirement clause inside the description prose.
# Order matters: combined pre/co requisite patterns come before the plain ones.
_LEADINS: list[tuple[str, str]] = [
    ("combined", r"Prerequisites?\s+or\s+co-?\s?requisites?\s*:?"),
    ("combined", r"Pre-?\s*(?:and|/|or)\s*co-?\s?requisites?\s*:?"),
    ("coreq", r"Co-?\s?requisites?\s*:?"),
    ("prereq", r"Prerequisites?\s*:?"),
    ("antireq", r"Antirequisites?\s*:?"),
    ("credit", r"Credit (?:cannot|may not|will not) be (?:obtained|granted)"),
    ("note", r"See Note|Notes?\s*:?"),
]

# Split the description into prereq/coreq/credit-exclusion strings by lead-in
# phrase. Longest non-overlapping match wins and the text is kept verbatim; no
# boolean prereq logic happens here.
def extract_requirements(description: str) -> tuple[dict[str, str | None], list[str]]:
    text = _clean(description)
    flags: list[str] = []

    markers: list[tuple[int, int, str]] = []
    for kind, pat in _LEADINS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            markers.append((m.start(), m.end(), kind))

    markers.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    kept: list[tuple[int, int, str]] = []
    covered = -1
    for start, end, kind in markers:
        if start >= covered:
            kept.append((start, end, kind))
            covered = end

    fields: dict[str, str | None] = {"prereq_raw": None, "coreq_raw": None, "credit_exclusion_raw": None}
    for i, (start, end, kind) in enumerate(kept):
        nxt = kept[i + 1][0] if i + 1 < len(kept) else len(text)

        seg_start = start if kind == "credit" else end
        value = _clean(text[seg_start:nxt]).rstrip()
        if not value:
            continue
        if kind == "prereq":
            if fields["prereq_raw"] is None:
                fields["prereq_raw"] = value
        elif kind == "coreq":
            if fields["coreq_raw"] is None:
                fields["coreq_raw"] = value
        elif kind == "combined":
            # "Prerequisite or corequisite" clauses go into both fields since
            # either reading is valid.
            if fields["prereq_raw"] is None:
                fields["prereq_raw"] = value
            if fields["coreq_raw"] is None:
                fields["coreq_raw"] = value
            flags.append("combined-prereq/coreq clause captured into both fields")
        elif kind == "credit":
            if fields["credit_exclusion_raw"] is None:
                fields["credit_exclusion_raw"] = value

    return fields, flags

def _dfs(node: Node, tags: set[str]):
    for child in node.iter(include_text=False):
        if child.tag in tags:
            yield child
        yield from _dfs(child, tags)

_TERM_RE = re.compile(r"^(Winter|Spring|Summer|Fall)\s+Term\s+\d{4}$")

def parse_section_cell(text: str) -> tuple[str, str, str | None, list[str]]:
    flags: list[str] = []
    t = _clean(text)
    m = re.match(r"^(?P<label>.+?)\s*\((?P<cid>[0-9A-Za-z]+)\)\s*$", t)
    if not m:

        flags.append(f"section-cell-no-classid:{t!r}")
        tokens = t.split()
        if not tokens:
            return ("", "", None, flags)
        if len(tokens) == 1:
            return (tokens[0], "", None, flags)
        return (" ".join(tokens[:-1]), tokens[-1], None, flags)

    label = m.group("label").strip()
    class_id = m.group("cid")
    tokens = label.split()
    if len(tokens) == 1:
        component, section = tokens[0], ""
        flags.append(f"section-cell-no-section-label:{t!r}")
    else:
        component, section = " ".join(tokens[:-1]), tokens[-1]
    return (component, section, class_id, flags)

def _class_times_cols(cell: Node) -> tuple[list[tuple[str, str]], str]:
    cols: list[tuple[str, str]] = []
    for col in cell.css("div.col"):
        txt = _clean(col.text())
        if not txt:
            continue
        html = col.html or ""
        if "fa-calendar" in html:
            cols.append(("date", txt))
        elif "fa-clock" in html:
            cols.append(("time", txt))
        else:

            if re.search(r"\d{4}-\d{2}-\d{2}", txt):
                cols.append(("date", txt))
            elif re.search(r"\d{1,2}:\d{2}", txt):
                cols.append(("time", txt))
            else:
                cols.append(("date", txt))
    return cols, _clean(cell.text())

def parse_section_row(row: Node, term: str, term_code: str | None) -> tuple[Section, list[str]]:
    flags: list[str] = []
    sec_cell = row.css_first('td[data-card-title="Section"]')
    cap_cell = row.css_first('td[data-card-title="Capacity"]')
    ct_cell = row.css_first('td[data-card-title="Class times"]')

    component = section = ""
    class_id = None
    if sec_cell is not None:
        component, section, class_id, f = parse_section_cell(sec_cell.text())
        flags += f
    else:
        flags.append("missing-section-cell")

    capacity = None
    if cap_cell is not None:
        cap_txt = _clean(cap_cell.text())
        capacity = _to_int(cap_txt)
        if capacity is None and cap_txt:
            flags.append(f"unparseable-capacity:{cap_txt!r}")

    meetings: list[dict] = []
    schedule_note = None
    if ct_cell is not None:
        cols, raw = _class_times_cols(ct_cell)
        if not cols:
            schedule_note = raw or "No scheduled meeting times"
        else:
            res = daycodes.parse_class_times(cols, raw)
            meetings = [m.as_dict() for m in res.meetings]
            schedule_note = res.schedule_note
            flags += res.flags
    else:
        flags.append("missing-class-times-cell")

    sid = f"{component} {section} ({class_id})".strip()
    flags = [f"[{term} {sid}] {fl}" for fl in flags]

    return (
        Section(
            term=term,
            term_code=term_code,
            component=component,
            section=section,
            class_id=class_id,
            capacity=capacity,
            meetings=meetings,
            schedule_note=schedule_note,
        ),
        flags,
    )

def parse_course(html: str, source_url: str, fetched_at: str | None = None) -> tuple[Course, list[str]]:
    tree = HTMLParser(html)
    flags: list[str] = []
    meta = _metas(tree)

    course_id = meta.get("ua__cat_course")
    subject = meta.get("ua__cat_subject")
    catalog = meta.get("ua__cat_catalog")

    # Meta tags are primary; fall back to the page h1 only if they are missing.
    if not (course_id and subject and catalog):
        flags.append(f"missing-course-meta:{source_url}")
        h1 = tree.css_first("h1")
        if h1 is not None:
            m = re.match(r"\s*([A-Z][A-Z &]*?)\s+([0-9][0-9A-Za-z]*)\b", _clean(h1.text()))
            if m:
                subject = subject or m.group(1)
                catalog = catalog or m.group(2)
                course_id = course_id or f"{m.group(1)} {m.group(2)}"

    course_id = course_id or "UNKNOWN"
    subject = subject or ""
    catalog = catalog or ""

    title = meta.get("ua__cat_coursetitle")
    credits = _to_float(meta.get("ua__cat_credits"))
    faculty = meta.get("ua__cat_faculty")
    career = meta.get("ua__cat_career")
    terms_offered = [t.strip() for t in meta.get("ua__cat_term", "").split(",") if t.strip()]
    meta_sections = _to_int(meta.get("ua__cat_sections"))
    meta_sections_online = _to_int(meta.get("ua__cat_sections_online"))

    units_string = None
    units_h2 = tree.css_first("h2.fs-5")
    if units_h2 is not None:
        units_string = _clean(units_h2.text())

    description_raw, no_desc_marker = _description_paragraph(tree)
    if description_raw is None and not no_desc_marker:
        flags.append(f"missing-description:{course_id}")

    reqs, req_flags = extract_requirements(description_raw or "")
    flags += [f"[{course_id}] {f}" for f in req_flags]
    if "Prerequisite" in (description_raw or "") and reqs["prereq_raw"] is None:
        flags.append(f"[{course_id}] prereq-leadin-present-but-unparsed")

    note_raw = None
    if description_raw:
        nm = re.search(r"(See Note.*|Note:.*)", description_raw, re.DOTALL)
        if nm:
            note_raw = _clean(nm.group(1)) or None

    sections, term_notes, sec_flags = _parse_sections(tree, description_raw)
    flags += sec_flags

    course = Course(
        course_id=course_id,
        subject=subject,
        catalog_number=catalog,
        title=title,
        credits=credits,
        faculty=faculty,
        career=career,
        units_string=units_string,
        description_raw=description_raw,
        prereq_raw=reqs["prereq_raw"],
        coreq_raw=reqs["coreq_raw"],
        credit_exclusion_raw=reqs["credit_exclusion_raw"],
        terms_offered=terms_offered,
        source_url=source_url,
        fetched_at=fetched_at,
        sections=[s.as_dict() for s in sections],
        note_raw=note_raw,
        term_notes=term_notes or None,
        meta_sections=meta_sections,
        meta_sections_online=meta_sections_online,
    )

    if meta_sections is not None and len(sections) != meta_sections:
        flags.append(
            f"[{course_id}] section-count-mismatch: parsed={len(sections)} meta={meta_sections}"
        )
    return course, flags

_NO_DESC = "There is no available course description"

def _description_paragraph(tree: HTMLParser) -> tuple[str | None, bool]:

    fac = tree.css_first('p a[href*="/catalogue/faculty/"]')
    if fac is not None:
        sib = fac.parent.next
        while sib is not None:
            txt = _clean(sib.text())
            if sib.tag == "p" and txt:
                return txt, False
            if sib.tag == "div":
                if _NO_DESC in txt:
                    return None, True

                break
            if sib.tag in ("table", "h2", "h3"):
                break
            sib = sib.next

    best = None
    for p in tree.css("p"):
        txt = _clean(p.text())
        if len(txt) > (len(best) if best else 40) and "breadcrumb" not in (p.attributes.get("class") or ""):
            if not p.css_first("a[href*='/catalogue/faculty/']"):
                best = txt
    if best is not None:
        return best, False
    if _NO_DESC in _clean(tree.body.text() if tree.body else ""):
        return None, True
    return None, False

def _parse_sections(
    tree: HTMLParser, top_description: str | None = None
) -> tuple[list[Section], dict, list[str]]:
    sections: list[Section] = []
    term_notes: dict[str, str] = {}
    flags: list[str] = []
    top_norm = _clean(top_description or "")

    body = tree.css_first("body") or tree.root
    nodes = list(_dfs(body, {"h2", "h3", "table", "p"}))

    # Walk the body in order, tracking the current term heading so each section
    # table is tagged with the term it sits under.
    current_term: str | None = None
    current_term_code: str | None = None
    awaiting_term_note = False

    for node in nodes:
        tag = node.tag
        if tag == "h2":
            txt = _clean(node.text())
            if _TERM_RE.match(txt):
                current_term = txt
                current_term_code = config.term_code_from_label(txt)
                if current_term_code is None:
                    flags.append(f"unknown-term-code:{txt!r}")
                awaiting_term_note = True

        elif tag == "p":
            if awaiting_term_note and current_term:
                txt = _clean(node.text())
                if len(txt) > 60:
                    awaiting_term_note = False
                    if txt != top_norm:
                        term_notes[current_term] = txt
                        flags.append(
                            f"[{current_term}] per-term-description differs from top "
                            "description (course-is-changing block)"
                        )
        elif tag == "h3":
            awaiting_term_note = False
        elif tag == "table":
            awaiting_term_note = False
            if not node.css_first('td[data-card-title="Section"]'):
                continue
            term = current_term or "Unknown"
            for row in node.css("tbody tr"):
                if row.css_first("td") is None:
                    continue
                sec, f = parse_section_row(row, term, current_term_code)
                if sec.component == "" and sec.section == "" and not sec.meetings:
                    continue
                sections.append(sec)
                flags += f

    return sections, term_notes, flags

_DEGREE_MAP = [
    ("Bachelor of Science in Nursing", "BScN"),
    ("Bachelor of Science in Engineering", "BSc Eng"),
    ("Bachelor of Science", "BSc"),
    ("Bachelor of Arts", "BA"),
    ("Bachelor of Education", "BEd"),
    ("Bachelor of Commerce", "BCom"),
    ("Bachelor of Kinesiology", "BKin"),
    ("Bachelor of Music", "BMus"),
    ("Bachelor of Design", "BDes"),
    ("Bachelor of", "B?"),
    ("Master of", "M?"),
    ("Doctor of", "D?"),
]

_COURSE_CODE_RE = re.compile(r"^([A-Z][A-Z&/]*(?:\s[A-Z&/]+)*)\s+(\d+[A-Z]*)\b")

def _degree_from_name(name: str | None) -> str | None:
    if not name:
        return None
    for prefix, code in _DEGREE_MAP:
        if name.startswith(prefix):
            return code
    return None

def _course_code_from_text(text: str) -> str | None:
    t = _clean(text)
    m = _COURSE_CODE_RE.match(t)
    if not m:
        return None
    return f"{_clean(m.group(1))} {m.group(2)}"

def _ancestor_core_headings(node: Node) -> list[str]:
    out: list[str] = []
    cur = node.parent
    while cur is not None:
        cls = cur.attributes.get("class") or ""
        if "acalog-core" in cls:
            h = _own_heading(cur)
            if h is not None:
                out.append(_clean(h.text()))
        cur = cur.parent
    out.reverse()
    return out

def _own_heading(block: Node) -> Node | None:
    for child in block.iter(include_text=False):
        if child.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            return child
    return None

def _direct_lis(core: Node) -> tuple[list[Node], list[Node]]:
    course_lis: list[Node] = []
    prose_lis: list[Node] = []

    def rec(n: Node) -> None:
        for ch in n.iter(include_text=False):
            cls = ch.attributes.get("class") or ""
            if "acalog-core" in cls:
                continue
            if ch.tag == "li":
                if "acalog-course" in cls:
                    course_lis.append(ch)
                else:
                    prose_lis.append(ch)
            rec(ch)

    rec(core)
    return course_lis, prose_lis

def _has_nested_core(core: Node) -> bool:
    for ch in core.iter(include_text=False):
        cls = ch.attributes.get("class") or ""
        if "acalog-core" in cls:
            return True
        if _has_nested_core(ch):
            return True
    return False

_RULE_RE = re.compile(r"(\d+\s*units?\b|\bfrom\b|★|\bone of\b|\beach of\b|\bunits? from\b)", re.I)

# Parse an Acalog program page into requirement blocks. Confidence drops to
# needs_review on unparseable course codes or empty rule blocks, and the raw
# HTML of any shaky block is dumped for manual checking.
def parse_program(
    html: str,
    poid: str,
    catoid: str,
    tier: str,
    source_url: str,
    fetched_at: str | None = None,
) -> tuple[Program, list[str], list[tuple[int, str]]]:
    tree = HTMLParser(html)
    flags: list[str] = []
    dumps: list[tuple[int, str]] = []

    content = tree.css_first("td.block_content") or tree.css_first(".block_content")
    program_name = None
    if content is not None:
        h1 = content.css_first("h1")
        if h1 is not None:
            program_name = _clean(h1.text())
    if program_name is None:
        t = tree.css_first("title")
        if t is not None:
            program_name = _clean(t.text()).split(" - University of Alberta")[0].replace("Program: ", "")

    degree = _degree_from_name(program_name)

    blocks: list[RequirementBlock] = []
    confidence = "high"

    if content is None:
        flags.append(f"[poid {poid}] no-block_content-container")
        confidence = "needs_review"
    else:
        cores = content.css("div.acalog-core")
        if not cores:
            flags.append(f"[poid {poid}] no-acalog-core-blocks")
            confidence = "needs_review"
        for idx, core in enumerate(cores):
            heading_node = _own_heading(core)
            own_heading = _clean(heading_node.text()) if heading_node is not None else ""

            path_parts = _ancestor_core_headings(core)
            heading_path = " / ".join([*path_parts, own_heading]) if own_heading else " / ".join(path_parts)

            course_lis, prose_lis = _direct_lis(core)
            courses: list[str] = []
            bad_codes = 0
            for li in course_lis:
                a = li.css_first("a")
                txt = a.text() if a is not None else li.text()
                code = _course_code_from_text(txt)
                if code:
                    courses.append(code)
                else:
                    bad_codes += 1
                    courses.append(_clean(txt))
            prose_items = [_clean(li.text()) for li in prose_lis if _clean(li.text())]

            rule_text = own_heading if (own_heading and _RULE_RE.search(own_heading)) else None
            if prose_items:
                base = rule_text or (own_heading or "")
                rule_text = _clean(f"{base} {'; '.join(prose_items)}") if base else "; ".join(prose_items)

            block_needs_review = False
            if (own_heading and _RULE_RE.search(own_heading)) and not courses and not prose_items:
                if not _has_nested_core(core):
                    block_needs_review = True
                    flags.append(f"[poid {poid}] rule-block-empty: {heading_path!r}")
            if bad_codes:
                block_needs_review = True
                flags.append(f"[poid {poid}] {bad_codes} unparseable course code(s) in {heading_path!r}")

            if block_needs_review:
                confidence = "needs_review"
                dumps.append((idx, core.html or ""))

            if own_heading or courses:
                blocks.append(
                    RequirementBlock(
                        heading=heading_path or own_heading,
                        rule_text_raw=rule_text,
                        courses=courses,
                    )
                )

    program = Program(
        poid=poid,
        program_name=program_name,
        degree=degree,
        catoid=catoid,
        tier=tier,
        requirement_blocks_raw=[b.as_dict() for b in blocks],
        source_url=source_url,
        fetched_at=fetched_at,
        parse_confidence=confidence,
    )
    return program, flags, dumps
