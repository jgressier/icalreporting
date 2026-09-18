import icalreporting.reporting as ir
from datetime import datetime, time, timedelta
from pathlib import Path

def test_init():
    prjname = "my_original_name"
    path = "examples/projectA"
    icallist = ir.IcalList(name=prjname, folder=path)
    assert icallist._name == prjname
    assert icallist._folder == path
    for d in (icallist._start, icallist._end):
        assert isinstance(d, datetime)
    assert icallist._start.date().isoformat() == ir._default_startdate
    assert (icallist._end-timedelta(days=1)).date().isoformat() == ir._default_enddate

def test_open():
    prjname = "my_original_name"
    path = "examples/projectA"
    icallist = ir.IcalList(name=prjname, folder=path)
    icallist.load_ics()
    assert len(icallist.members()) == 2

def test_properties():
    prjname = "my_original_name"
    path = "examples/projectA"
    project = ir.Project(name=prjname, folder=path)
    project.load_ics()


def test_all_day_event():
    dataframe = ir.ical_to_dframe(
        Path("examples/example_variations.ics"),
        datetime(2024, 11, 1),
        datetime(2024, 12, 1),
    )

    event = dataframe[dataframe["name"] == "All Day Workshop"].iloc[0]
    assert event["h_begin"] == time(9)
    assert event["duration"] == 8.0


def test_multiday_all_day_event(tmp_path):
    filename = tmp_path / "multiday.ics"
    filename.write_text(
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//icalreporting//tests//EN\n"
        "BEGIN:VEVENT\n"
        "UID:multiday-test\n"
        "DTSTAMP:20240101T000000Z\n"
        "DTSTART;VALUE=DATE:20241114\n"
        "DTEND;VALUE=DATE:20241116\n"
        "SUMMARY:Two Day Workshop\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )

    dataframe = ir.ical_to_dframe(
        filename,
        datetime(2024, 11, 1),
        datetime(2024, 12, 1),
    )

    event = dataframe.iloc[0]
    assert event["h_begin"] == time(9)
    assert event["duration"] == 16.0
