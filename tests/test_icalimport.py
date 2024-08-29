import icalreporting.reporting as ir
from datetime import datetime, timedelta

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
