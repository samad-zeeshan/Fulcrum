import parsers

SYNTH = """
<html><head>
<meta name="ua__cat_course" content="TEST 999">
<meta name="ua__cat_subject" content="TEST">
<meta name="ua__cat_catalog" content="999">
<meta name="ua__cat_coursetitle" content="Edge Cases">
<meta name="ua__cat_credits" content="3.00">
<meta name="ua__cat_career" content="UGRD">
<meta name="ua__cat_term" content="Fall Term 2026">
<meta name="ua__cat_sections" content="3">
</head><body>
<div class="container">
<h1>TEST 999 - Edge Cases</h1>
<h2 class="fs-5">3 units (fi 6)(EITHER, 3-0-3)</h2>
<p><a href="/catalogue/faculty/sc">Faculty of Science</a></p>
<p>A test course. Prerequisite: TEST 100 or consent of Department. Corequisite: TEST 101.</p>
<h2>Fall Term 2026</h2>
<h3>Lectures</h3>
<table><thead><tr><th>Section</th><th>Capacity</th><th>Class times</th><th>x</th></tr></thead>
<tbody>
<tr>
  <td data-card-title="Section"><div>WORK EXPERIENCE A1<br>(11111)</div></td>
  <td data-card-title="Capacity"><span>0</span></td>
  <td data-card-title="Class times"><div><div class="row"><div class="col"><span class="far fa-calendar"></span> 2026-09-01 - 2026-12-08 (MWF)</div><div class="col"><span class="far fa-clock"></span> 13:00 - 13:50</div></div></div></td>
  <td data-card-title="Instructor(s)"></td>
</tr>
<tr>
  <td data-card-title="Section"><div>LECTURE 800<br>(22222)</div></td>
  <td data-card-title="Capacity"><span>30</span></td>
  <td data-card-title="Class times"><div><div class="row"><div class="col"><span class="far fa-calendar"></span> 2026-09-01 - 2026-12-08</div></div></div></td>
  <td data-card-title="Instructor(s)"></td>
</tr>
<tr>
  <td data-card-title="Section"><div>LAB D01<br>(33333)</div></td>
  <td data-card-title="Capacity"><span>25</span></td>
  <td data-card-title="Class times"><div><div class="row"><div class="col"><span class="far fa-calendar"></span> 2026-09-01 - 2026-12-08 (S)</div><div class="col"><span class="far fa-clock"></span> 9:00 - 11:50</div></div></div></td>
  <td data-card-title="Instructor(s)"></td>
</tr>
</tbody></table>
</div></body></html>
"""

def test_edge_sections():
    c, flags = parsers.parse_course(SYNTH, "http://x", "t")
    d = c.as_dict()
    secs = {s["class_id"]: s for s in d["sections"]}
    assert len(secs) == 3

    we = secs["11111"]
    assert we["component"] == "WORK EXPERIENCE"
    assert we["section"] == "A1"
    assert we["capacity"] == 0
    assert we["meetings"][0]["days"] == ["M", "W", "F"]

    online = secs["22222"]
    assert online["component"] == "LECTURE" and online["section"] == "800"
    assert online["meetings"] == []
    assert online["schedule_note"] == "2026-09-01 - 2026-12-08"

    lab = secs["33333"]
    assert lab["meetings"][0]["days"] == ["S"]
    assert lab["meetings"][0]["time_start"] == "09:00"
    assert any("unknown-day-code" in f for f in flags)

def test_requirements_extracted_with_consent_text():
    c, _ = parsers.parse_course(SYNTH, "http://x", "t")
    d = c.as_dict()
    assert d["prereq_raw"] == "TEST 100 or consent of Department."
    assert d["coreq_raw"] == "TEST 101."
