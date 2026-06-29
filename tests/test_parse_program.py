import re
from pathlib import Path

import parsers

FIX = Path(__file__).parent / "fixtures" / "program_110935.html"
URL = "https://calendar.ualberta.ca/preview_program.php?catoid=69&poid=110935"

def _parse():
    return parsers.parse_program(FIX.read_text(encoding="utf-8"), "110935", "69", "gold", URL, "t")

def test_program_metadata():
    p, _, _ = _parse()
    d = p.as_dict()
    assert d["poid"] == "110935"
    assert d["catoid"] == "69"
    assert d["tier"] == "gold"
    assert "Computing Science" in (d["program_name"] or "")
    assert d["degree"] == "BSc"

def test_requirement_blocks_have_courses():
    p, _, _ = _parse()
    d = p.as_dict()
    blocks = d["requirement_blocks_raw"]
    assert len(blocks) > 10
    with_courses = [b for b in blocks if b["courses"]]
    assert len(with_courses) > 10

    found = {tuple(b["courses"]) for b in blocks if b["heading"].endswith("Foundation Courses")}
    assert any("CMPUT 174" in c and "CMPUT 175" in c for c in found)

def test_courses_are_plain_strings_no_logic():
    p, _, _ = _parse()
    for b in p.as_dict()["requirement_blocks_raw"]:
        assert isinstance(b["courses"], list)
        for c in b["courses"]:
            assert isinstance(c, str)

def test_course_codes_well_formed():
    p, _, _ = _parse()
    code_re = re.compile(r"^[A-Z][A-Z&/ ]*\s\d+[A-Z]*$")
    sample = []
    for b in p.as_dict()["requirement_blocks_raw"]:
        sample += b["courses"]

    clean = [c for c in sample if code_re.match(c)]
    assert len(clean) > 30

def test_prose_rule_captured_verbatim():
    p, _, _ = _parse()
    rules = [b["rule_text_raw"] for b in p.as_dict()["requirement_blocks_raw"] if b["rule_text_raw"]]
    assert any("any 300- and 400-level CMPUT course" in (r or "") for r in rules)

def test_confidence_high_and_no_dumps():
    p, flags, dumps = _parse()
    assert p.as_dict()["parse_confidence"] == "high"
    assert dumps == []

def test_deterministic():
    a, _, _ = _parse()
    b, _, _ = _parse()
    assert a.as_dict() == b.as_dict()
