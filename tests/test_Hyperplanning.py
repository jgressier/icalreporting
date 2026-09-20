from datetime import datetime, timedelta

from openpyxl import Workbook, load_workbook
import pytest

import icalreporting.reporting as ir


@pytest.fixture(scope="module")
def planning():
    loaded_planning = ir.Hyperplanning(name="planning", folder="examples/planningA")
    loaded_planning.load_ics()
    return loaded_planning


def test_init():
    prjname = "my_original_name"
    path = "examples/planningA"
    planning = ir.Hyperplanning(name=prjname, folder=path)
    assert planning._name == prjname
    assert planning._folder == path
    for date in (planning._start, planning._end):
        assert isinstance(date, datetime)
    assert planning._start.date().isoformat() == ir._default_startdate
    assert (planning._end - timedelta(days=1)).date().isoformat() == ir._default_enddate


def test_open(planning):
    assert planning.members() == {"JG"}
    assert len(planning.courses()) == 9
    assert len(planning._dframe) == 60


def test_properties(planning):
    assert {"Course", "CourseType"} <= set(planning._dframe.columns)
    assert {"BE", "C*", "Cours", "Oral", "PC", "unknown"} <= set(
        planning._dframe["CourseType"]
    )


def test_filter():
    planning = ir.Hyperplanning(name="filtered", folder="examples/planningA")
    planning.load_ics()
    planning.filter(start="2023-01-01", end="2023-12-31")

    assert len(planning._dframe) == 39
    assert {event.year for event in planning._dframe["date"]} == {2023}


def test_course_worksheet(planning):
    wb = Workbook()
    ws = planning.add_tab_course(wb, "F-DF301")
    rows = list(ws.values)

    assert ws.title == "F-DF301"
    assert set(rows[0][1:]) == {"Cours", "Oral", "PC"}
    assert sum(value for value in rows[1][1:] if value is not None) == 14.5


def test_write_workbook(planning, tmp_path):
    wb = planning.workbook()
    assert set(wb.sheetnames) == {"Synthèse", "JG"}
    assert wb["Synthèse"]["A2"].value == "BE"
    assert wb["JG"].max_row == 61

    output = tmp_path / "planning.xlsx"
    wb.save(output)
    reloaded = load_workbook(output, read_only=True)
    assert reloaded.sheetnames == wb.sheetnames
    reloaded.close()
