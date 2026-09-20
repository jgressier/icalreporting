from datetime import datetime, timedelta

from openpyxl import load_workbook
import pytest

import icalreporting.reporting as ir


@pytest.fixture(scope="module")
def project():
    loaded_project = ir.Project(name="project", folder="examples/projectA")
    loaded_project.load_ics()
    return loaded_project


def test_init():
    prjname = "my_original_name"
    path = "examples/projectA"
    project = ir.Project(name=prjname, folder=path)
    assert project._name == prjname
    assert project._folder == path
    for date in (project._start, project._end):
        assert isinstance(date, datetime)
    assert project._start.date().isoformat() == ir._default_startdate
    assert (project._end - timedelta(days=1)).date().isoformat() == ir._default_enddate


def test_open(project):
    assert project.members() == {"Abraracourcix", "Falbala"}
    assert project.work_packages() == {"No_WP", "WP", "WP0", "WP1", "WP2", "WPA"}
    assert len(project._dframe) == 403


def test_properties(project):
    assert {"date", "duration", "name", "Member", "WP"} <= set(project._dframe.columns)
    assert project._dframe.loc[project._dframe["WP"] == "WP1", "duration"].sum() == 382.25


def test_filter():
    project = ir.Project(name="filtered", folder="examples/projectA")
    project.load_ics()
    project.filter(start="2023-01-01", end="2023-12-31")

    assert len(project._dframe) == 74
    assert {event.year for event in project._dframe["date"]} == {2023}


def test_write_workbook(project, tmp_path):
    wb = project.workbook()
    assert set(wb.sheetnames) == {
        "Synthèse",
        "Abraracourcix",
        "Falbala",
        "No_WP",
        "WP",
        "WP0",
        "WP1",
        "WP2",
        "WPA",
    }
    assert wb["Synthèse"]["A2"].value == "Abraracourcix"
    assert wb["Synthèse"]["B2"].value == 24.75

    output = tmp_path / "project.xlsx"
    wb.save(output)
    reloaded = load_workbook(output, read_only=True)
    assert reloaded.sheetnames == wb.sheetnames
    reloaded.close()
