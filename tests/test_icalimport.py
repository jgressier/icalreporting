import icalreporting.reporting as ir
from datetime import datetime, timedelta

def test_init():
    prjname = "my_original_name"
    path = "examples/ProjectA"
    project = ir.Project(name=prjname, folder=path)
    assert project._name == prjname
    assert project._folder == path
    for d in (project._start, project._end):
        assert isinstance(d, datetime)
    assert project._start.date().isoformat() == ir._default_startdate
    assert (project._end-timedelta(days=1)).date().isoformat() == ir._default_enddate

def test_open():
    prjname = "my_original_name"
    path = "examples/ProjectA"
    project = ir.Project(name=prjname, folder=path)
    project.load_ics()
    assert len(project.members()) == 2
    assert len(project.work_packages()) == 6

def test_properties():
    prjname = "my_original_name"
    path = "examples/ProjectA"
    project = ir.Project(name=prjname, folder=path)
    project.load_ics()

def test_write_workbook():
    prjname = "my_original_name"
    path = "examples/ProjectA"
    project = ir.Project(name=prjname, folder=path)
    project.load_ics()
    wb = project.workbook()
