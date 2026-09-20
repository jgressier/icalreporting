from datetime import datetime, time, timedelta
from pathlib import Path

import pytest

import icalreporting.reporting as ir


def test_init():
    prjname = "my_original_name"
    path = "examples/projectA"
    icallist = ir.IcalList(name=prjname, folder=path)
    assert icallist._name == prjname
    assert icallist._folder == path
    for date in (icallist._start, icallist._end):
        assert isinstance(date, datetime)
    assert icallist._start.date().isoformat() == ir._default_startdate
    assert (icallist._end - timedelta(days=1)).date().isoformat() == ir._default_enddate


def test_open():
    icallist = ir.IcalList(name="list", folder="examples/projectA")
    icallist.load_ics()
    assert icallist.members() == {"Abraracourcix", "Falbala"}


def test_missing_ics_files(tmp_path):
    icallist = ir.IcalList(name="empty", folder=tmp_path)

    with pytest.raises(FileNotFoundError, match=r"no \*\.ics file found"):
        icallist.load_ics()


def test_all_day_event():
    dataframe = ir.ical_to_dframe(
        Path("examples/example_variations.ics"),
        datetime(2024, 11, 1),
        datetime(2024, 12, 1),
    )

    event = dataframe[dataframe["name"] == "All Day Workshop"].iloc[0]
    assert event["h_begin"] == time(9)
    assert event["duration"] == 8.0

    timed_event = dataframe[dataframe["name"] == "Client Call"].iloc[0]
    assert timed_event["h_begin"] == time(14)
    assert timed_event["duration"] == 1.0


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
        "END:VCALENDAR\n",
        encoding="utf-8",
    )

    dataframe = ir.ical_to_dframe(
        filename,
        datetime(2024, 11, 1),
        datetime(2024, 12, 1),
    )

    event = dataframe.iloc[0]
    assert event["h_begin"] == time(9)
    assert event["duration"] == 16.0
