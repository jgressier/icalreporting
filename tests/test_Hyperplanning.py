import icalreporting.reporting as ir
from datetime import datetime, timedelta

def test_init():
    prjname = "my_original_name"
    path = "examples/planningA"
    planning = ir.Hyperplanning(name=prjname, folder=path)
    assert planning._name == prjname
    assert planning._folder == path
    for d in (planning._start, planning._end):
        assert isinstance(d, datetime)
    assert planning._start.date().isoformat() == ir._default_startdate
    assert (planning._end-timedelta(days=1)).date().isoformat() == ir._default_enddate

def test_open():
    prjname = "my_original_name"
    path = "examples/planningA"
    planning = ir.Hyperplanning(name=prjname, folder=path)
    planning.load_ics()
    assert len(planning.members()) == 1
    assert len(planning.courses()) == 9

def test_properties():
    prjname = "my_original_name"
    path = "examples/planningA"
    planning = ir.Hyperplanning(name=prjname, folder=path)
    planning.load_ics()

def test_write_workbook():
    prjname = "my_original_name"
    path = "examples/planningA"
    planning = ir.Hyperplanning(name=prjname, folder=path)
    planning.load_ics()
    wb = planning.workbook()
    wb.save(prjname+".xlsx")
