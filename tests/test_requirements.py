import parsers

def _req(text):
    fields, flags = parsers.extract_requirements(text)
    return fields, flags

def test_colon_form():
    f, _ = _req("Some desc. Prerequisite: MATH 100. Note: x")
    assert f["prereq_raw"] == "MATH 100."

def test_no_colon_form():

    f, _ = _req("Some desc. Prerequisite CHEM 101 or 103. Note: x")
    assert f["prereq_raw"] == "CHEM 101 or 103."

def test_prereq_and_separate_coreq():
    f, _ = _req("Prerequisite CHEM 101 or 103. Corequisite: CHEM 264.")
    assert f["prereq_raw"] == "CHEM 101 or 103."
    assert f["coreq_raw"] == "CHEM 264."

def test_prereq_plus_combined_does_not_swallow():

    f, flags = _req("Prerequisite CHEM 101 or 103. Prerequisite or co-requisite: CHEM 264. Note: x")
    assert f["prereq_raw"] == "CHEM 101 or 103."
    assert f["coreq_raw"] == "CHEM 264."
    assert any("combined" in fl for fl in flags)

def test_credit_exclusion_is_verbatim_including_leadin():
    text = "Desc. Prerequisite: X. Credit cannot be obtained for A if credit obtained for B, C."
    f, _ = _req(text)
    assert f["credit_exclusion_raw"].startswith("Credit cannot be obtained for A")
    assert "B, C" in f["credit_exclusion_raw"]

def test_absent_fields_are_none_not_empty():
    f, _ = _req("Just a description with no requirements.")
    assert f["prereq_raw"] is None
    assert f["coreq_raw"] is None
    assert f["credit_exclusion_raw"] is None

def test_no_boolean_logic_anywhere():
    f, _ = _req("Prerequisite: MATH 100 and (STAT 151 or STAT 161).")

    assert isinstance(f["prereq_raw"], str)
    assert f["prereq_raw"] == "MATH 100 and (STAT 151 or STAT 161)."
