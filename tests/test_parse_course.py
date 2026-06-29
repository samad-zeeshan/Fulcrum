from pathlib import Path

import parsers

FIX = Path(__file__).parent / "fixtures" / "course_cmput_174.html"
URL = "https://apps.ualberta.ca/catalogue/course/cmput/174"

def _parse():
    return parsers.parse_course(FIX.read_text(encoding="utf-8"), URL, "2026-06-28T00:00:00Z")

def test_meta_fields():
    c, _ = _parse()
    d = c.as_dict()
    assert d["course_id"] == "CMPUT 174"
    assert d["subject"] == "CMPUT"
    assert d["catalog_number"] == "174"
    assert d["title"] == "Introduction to the Foundations of Computation I"
    assert d["credits"] == 3.0
    assert d["career"] == "UGRD"
    assert d["faculty"] == "Faculty of Science"
    assert d["units_string"] == "3 units (fi 6)(EITHER, 3-0-3)"
    assert d["terms_offered"] == ["Spring Term 2026", "Fall Term 2026", "Winter Term 2027"]

def test_requirement_strings_are_verbatim_and_not_logic():
    c, _ = _parse()
    d = c.as_dict()
    assert d["prereq_raw"] == "Math 30, 30-1, or 30-2."
    assert d["coreq_raw"] is None
    assert d["credit_exclusion_raw"].startswith("Credit cannot be obtained for CMPUT 174")

    for field in ("prereq_raw", "coreq_raw", "credit_exclusion_raw"):
        assert d[field] is None or isinstance(d[field], str)

def test_section_count_matches_meta():
    c, flags = _parse()
    d = c.as_dict()
    assert d["meta_sections"] == 55
    assert len(d["sections"]) == 55
    assert not any("section-count-mismatch" in f for f in flags)

def test_term_codes_assigned():
    c, _ = _parse()
    by_term = {s["term"]: s["term_code"] for s in c.as_dict()["sections"]}
    assert by_term["Spring Term 2026"] == "1950"
    assert by_term["Fall Term 2026"] == "1970"
    assert by_term["Winter Term 2027"] == "1980"

def test_login_gated_fields_always_null():
    c, _ = _parse()
    for s in c.as_dict()["sections"]:
        assert s["instructor"] is None
        assert s["location"] is None

def test_section_grammar_parsed():
    c, _ = _parse()
    secs = {(s["component"], s["section"]): s for s in c.as_dict()["sections"]}
    lec = secs[("LECTURE", "A2")]
    assert lec["class_id"] == "52329"
    assert lec["capacity"] >= 0
    m = lec["meetings"][0]
    assert m["days"] == ["T", "R"]
    assert m["time_start"] == "09:30" and m["time_end"] == "10:50"

def test_per_term_changing_description_captured():
    c, _ = _parse()

    notes = c.as_dict().get("term_notes") or {}
    assert "Fall Term 2026" in notes
    assert notes["Fall Term 2026"] != c.as_dict()["description_raw"]

def test_deterministic():
    a, _ = _parse()
    b, _ = _parse()
    assert a.as_dict() == b.as_dict()
