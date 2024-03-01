import icalreporting.reporting as ir
from datetime import datetime

def test_open():
    prjname = "my_original_name"
    path = "example/ProjectA"
    project = ir.Project(name=prjname, folder=path)
    assert project._name == prjname
    assert project._folder == path
    assert project._start == datetime.fromisoformat(ir._default_startdate)
    assert project._end == datetime.fromisoformat(ir._default_enddate)

def test_properties():
    assert True