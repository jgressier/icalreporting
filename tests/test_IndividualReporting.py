from datetime import date, datetime

from openpyxl import load_workbook
import pandas as pd
import pytest

from icalreporting.reporting import IndividualReporting


CALENDAR = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//icalreporting//tests//EN
BEGIN:VEVENT
UID:early
DTSTAMP:20240101T000000Z
DTSTART;TZID=Europe/Paris:20240108T060000
DTEND;TZID=Europe/Paris:20240108T080000
SUMMARY:A/X early
END:VEVENT
BEGIN:VEVENT
UID:overlap
DTSTAMP:20240101T000000Z
DTSTART;TZID=Europe/Paris:20240108T073000
DTEND;TZID=Europe/Paris:20240108T090000
SUMMARY:A/Y overlap
END:VEVENT
BEGIN:VEVENT
UID:weekend
DTSTAMP:20240101T000000Z
DTSTART;TZID=Europe/Paris:20240113T100000
DTEND;TZID=Europe/Paris:20240113T120000
SUMMARY:B/Z weekend
END:VEVENT
BEGIN:VEVENT
UID:late
DTSTAMP:20240101T000000Z
DTSTART;TZID=Europe/Paris:20240116T180000
DTEND;TZID=Europe/Paris:20240116T200000
SUMMARY:B/Z late
END:VEVENT
BEGIN:VEVENT
UID:all-day
DTSTAMP:20240101T000000Z
DTSTART;VALUE=DATE:20240117
DTEND;VALUE=DATE:20240118
SUMMARY:A/X all day
END:VEVENT
BEGIN:VEVENT
UID:unclassified
DTSTAMP:20240101T000000Z
DTSTART;TZID=Europe/Paris:20240118T120000
DTEND;TZID=Europe/Paris:20240118T130000
SUMMARY:Administration
END:VEVENT
END:VCALENDAR
"""


@pytest.fixture
def calendar_folder(tmp_path):
    (tmp_path / "individual.ics").write_text(CALENDAR, encoding="utf-8")
    return tmp_path


@pytest.fixture
def reporting(calendar_folder):
    report = IndividualReporting(
        "individual",
        calendar_folder,
        start="2024-01-01",
        end="2024-02-29",
    )
    report.load_ics()
    return report


def test_requires_one_calendar(tmp_path):
    report = IndividualReporting("individual", tmp_path)
    with pytest.raises(ValueError, match="exactly one ICS file; found 0"):
        report.load_ics()

    (tmp_path / "first.ics").write_text(CALENDAR, encoding="utf-8")
    (tmp_path / "second.ics").write_text(CALENDAR, encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one ICS file; found 2"):
        report.load_ics()


def test_summary_parsing(reporting):
    assert set(reporting._dframe["Sector"]) == {"A", "B", "UNCLASSIFIED"}
    assert set(reporting._dframe["Subsector"]) == {"X", "Y", "Z", "UNCLASSIFIED"}
    early = reporting._dframe[reporting._dframe["name"] == "A/X early"].iloc[0]
    assert (early["Sector"], early["Subsector"], early["Comment"]) == ("A", "X", "early")
    unclassified = reporting._dframe[reporting._dframe["name"] == "Administration"].iloc[0]
    assert unclassified["Category"] == "UNCLASSIFIED/UNCLASSIFIED"
    assert unclassified["Comment"] == "Administration"


@pytest.mark.parametrize("summary", [None, float("nan"), pd.NA])
def test_missing_summary_is_unclassified(summary):
    assert IndividualReporting._parse_summary(summary) == (
        "UNCLASSIFIED",
        "UNCLASSIFIED",
        "",
    )


def test_overlap_correction(reporting):
    overlap = reporting._overlaps.iloc[0]
    assert overlap["first_name"] == "A/X early"
    assert overlap["second_name"] == "A/Y overlap"
    assert overlap["overlap_hours"] == 0.5
    assert overlap["corrected"]

    first = reporting._dframe[reporting._dframe["name"] == "A/X early"].iloc[0]
    assert first["end"] == datetime.fromisoformat("2024-01-08T07:30:00+01:00")
    assert first["duration"] == 1.5
    assert reporting.check_overlaps().empty

    with pytest.raises(ValueError, match="overlap mode"):
        reporting.check_overlaps(mode="invalid")


def test_overlap_warning(calendar_folder):
    report = IndividualReporting("individual", calendar_folder, start="2024-01-01", end="2024-02-29")
    with pytest.warns(UserWarning, match="1 overlapping event pair"):
        report.load_ics(overlap_mode="warn")

    assert not report._overlaps.iloc[0]["corrected"]


def test_weekly_report(reporting):
    weekly = reporting.weekly_report()

    assert list(weekly.columns[:2]) == ["Total", "Off hours"]
    assert weekly.loc["2024-01-07", "A/X"] == 1.5
    assert weekly.loc["2024-01-07", "A/Y"] == 1.5
    assert weekly.loc["2024-01-07", "B/Z"] == 2.0
    assert weekly.loc["2024-01-07", "Total"] == 5.0
    assert weekly.loc["2024-01-07", "Off hours"] == 3.0
    assert weekly.loc["2024-01-14", "A/X"] == 8.0
    assert weekly.loc["2024-01-14", "Total"] == 10.0
    assert weekly.loc["2024-01-14", "Off hours"] == 1.0
    assert "UNCLASSIFIED/UNCLASSIFIED" not in weekly.columns

    sectors = reporting.weekly_report(by="sector")
    assert sectors.loc["2024-01-07", "A"] == 3.0
    assert sectors.loc["2024-01-07", "B"] == 2.0

    with pytest.raises(ValueError, match="grouping"):
        reporting.weekly_report(by="invalid")


def test_last_four_complete_weeks(reporting):
    weekly = reporting.last_complete_weeks(as_of=date(2024, 2, 5))

    assert weekly.index.name == "Monday"
    assert list(weekly.index) == ["2024-01-08", "2024-01-15", "2024-01-22", "2024-01-29"]
    assert weekly.loc["2024-01-08", "Total"] == 5.0
    assert weekly.loc["2024-01-22", "Total"] == 0

    with pytest.raises(ValueError, match="weeks must be positive"):
        reporting.last_complete_weeks(weeks=0)


def test_workbook(reporting, tmp_path):
    output = tmp_path / "individual.xlsx"
    reporting.workbook().save(output)

    workbook = load_workbook(output, read_only=True)
    assert workbook.sheetnames == ["Weekly", "Weekly details", "Unclassified", "Overlaps"]
    assert workbook["Weekly"]["A1"].value == "Week"
    assert workbook["Weekly"]["B1"].value == "Monday"
    assert workbook["Weekly"]["C1"].value == "Total"
    assert workbook["Weekly"]["A3"].value == "W02"
    assert workbook["Weekly"]["B3"].value.date() == date(2024, 1, 8)
    assert workbook["Weekly"]["E1"].value == "A"
    assert workbook["Weekly"]["E3"].value == 3.0
    assert workbook["Weekly details"]["E1"].value == "A"
    assert workbook["Weekly details"]["E2"].value == "X"
    assert workbook["Weekly details"]["G2"].value == "Total"
    assert workbook["Unclassified"].max_row == 2
    assert workbook["Unclassified"]["D2"].value == "Administration"
    assert workbook["Overlaps"].max_row == 2
    workbook.close()


class FakeSMTP:
    instance = None

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.tls = False
        self.credentials = None
        self.message = None
        FakeSMTP.instance = self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        self.tls = True

    def login(self, username, password):
        self.credentials = (username, password)

    def send_message(self, message):
        self.message = message


def test_email(reporting):
    message = reporting.send_email(
        "recipient@example.com",
        "sender@example.com",
        "smtp.example.com",
        username="user",
        password="secret",
        as_of=date(2024, 2, 5),
        smtp_factory=FakeSMTP,
    )

    smtp = FakeSMTP.instance
    assert (smtp.host, smtp.port) == ("smtp.example.com", 587)
    assert smtp.tls
    assert smtp.credentials == ("user", "secret")
    assert smtp.message is message
    assert message["To"] == "recipient@example.com"
    assert "2024-01-08" in message.get_content()
    assert "A/X" not in message.get_content()

    with pytest.raises(ValueError, match="required"):
        reporting.build_email("", "sender@example.com")
    with pytest.raises(ValueError, match="smtp_host"):
        reporting.send_email("to@example.com", "from@example.com", "")
