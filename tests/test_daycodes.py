import daycodes

def _cols(*pairs):
    return list(pairs)

def test_expand_day_codes_known():
    codes, unknown = daycodes.expand_day_codes("MTWR")
    assert codes == ["M", "T", "W", "R"]
    assert unknown == []

def test_expand_day_codes_unknown_kept_and_flagged():
    codes, unknown = daycodes.expand_day_codes("MSF")
    assert codes == ["M", "S", "F"]
    assert unknown == ["S"]

def test_parse_date_col_with_days():
    mtg, unknown = daycodes.parse_date_col("2026-09-01 - 2026-12-08 (TR)")
    assert mtg.date_start == "2026-09-01"
    assert mtg.date_end == "2026-12-08"
    assert mtg.days == ["T", "R"]
    assert unknown == []

def test_parse_date_col_without_days():
    mtg, _ = daycodes.parse_date_col("2026-09-01 - 2026-12-08")
    assert mtg.days == []

def test_parse_single_date_col():

    mtg, _ = daycodes.parse_date_col("2026-09-18")
    assert mtg.date_start == "2026-09-18"
    assert mtg.date_end == "2026-09-18"
    assert mtg.days == []

def test_single_date_with_time_is_a_meeting():
    res = daycodes.parse_class_times(
        _cols(("date", "2026-09-18"), ("time", "08:00 - 10:50")), "raw"
    )
    assert len(res.meetings) == 1
    assert res.meetings[0].date_start == res.meetings[0].date_end == "2026-09-18"

def test_parse_time_col_pads_hour():
    assert daycodes.parse_time_col("9:00 - 9:50") == ("09:00", "09:50")
    assert daycodes.parse_time_col("10:00 - 11:25") == ("10:00", "11:25")

def test_single_meeting():
    res = daycodes.parse_class_times(
        _cols(("date", "2026-05-04 - 2026-06-10 (MTWR)"), ("time", "10:00 - 11:25")),
        "raw",
    )
    assert len(res.meetings) == 1
    m = res.meetings[0]
    assert m.days == ["M", "T", "W", "R"]
    assert m.time_start == "10:00" and m.time_end == "11:25"
    assert res.schedule_note is None
    assert res.flags == []

def test_multi_meeting():
    res = daycodes.parse_class_times(
        _cols(
            ("date", "2027-01-04 - 2027-04-09 (M)"), ("time", "09:00 - 09:50"),
            ("date", "2027-01-04 - 2027-04-09 (W)"), ("time", "11:00 - 11:50"),
        ),
        "raw",
    )
    assert len(res.meetings) == 2
    assert res.meetings[0].days == ["M"]
    assert res.meetings[1].days == ["W"]

def test_duplicate_meetings_deduped():

    res = daycodes.parse_class_times(
        _cols(
            ("date", "2027-01-04 - 2027-04-09 (M)"), ("time", "09:00 - 09:50"),
            ("date", "2027-01-04 - 2027-04-09 (M)"), ("time", "09:00 - 09:50"),
            ("date", "2027-01-04 - 2027-04-09 (M)"), ("time", "09:00 - 09:50"),
        ),
        "raw",
    )
    assert len(res.meetings) == 1

def test_online_no_time_yields_no_meeting_but_note():
    res = daycodes.parse_class_times(_cols(("date", "2026-09-01 - 2026-12-08")), "2026-09-01 - 2026-12-08")
    assert res.meetings == []
    assert res.schedule_note == "2026-09-01 - 2026-12-08"

def test_empty_cell():
    res = daycodes.parse_class_times([], "")
    assert res.meetings == []
    assert res.schedule_note == "No scheduled meeting times"

def test_unknown_day_code_flagged_not_crashing():
    res = daycodes.parse_class_times(
        _cols(("date", "2026-09-01 - 2026-12-08 (S)"), ("time", "10:00 - 11:00")),
        "raw",
    )
    assert len(res.meetings) == 1
    assert res.meetings[0].days == ["S"]
    assert any("unknown-day-code" in f for f in res.flags)
