from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from icalreporting.icaltools import IcalFile


EXAMPLE = Path("examples/example_variations.ics")


def test_icalfile_init():
    icalfile = IcalFile(EXAMPLE)
    assert icalfile._engine == "icalendar"
    assert icalfile._filename == EXAMPLE
    assert icalfile._calendar is None


def test_icalfile_read_icalendar():
    icalfile = IcalFile(EXAMPLE, engine="icalendar")
    icalfile.read()
    assert icalfile._calendar is not None
    assert icalfile.nevents() == 7


def test_icalfile_read_ical():
    icalfile = IcalFile(EXAMPLE, engine="ical")
    icalfile.read()
    assert icalfile._calendar is not None
    assert icalfile.nevents() == 7


@pytest.mark.parametrize("engine", ["icalendar", "ical"])
def test_icalfile_filter_summary(engine):
    icalfile = IcalFile(EXAMPLE, engine=engine)
    icalfile.read()
    filtered_events = icalfile.filter_summary(["team"])
    assert len(filtered_events) == 2
    assert icalfile.nevents() == 2


@pytest.mark.parametrize("engine", ["icalendar", "ical"])
def test_icalfile_write(engine, tmp_path):
    icalfile = IcalFile(EXAMPLE, engine=engine)
    icalfile.read()
    output = tmp_path / f"output-{engine}.ics"
    icalfile.write(output)

    written = IcalFile(output, engine=engine, verbose=False)
    written.read()
    assert written.nevents() == 7


def test_icalfile_invalid_engine():
    with pytest.raises(ValueError, match="Unsupported engine"):
        IcalFile(EXAMPLE, engine="invalid").read()


@pytest.mark.parametrize(
    "method, args",
    [
        ("nevents", ()),
        ("filter_summary", (["test"],)),
        ("clean_events", ()),
        ("normalize_vtimezone", ()),
        ("write", ("unused.ics",)),
    ],
)
def test_icalfile_calendar_not_loaded(method, args):
    icalfile = IcalFile(EXAMPLE)
    with pytest.raises(ValueError, match="Calendar not loaded"):
        getattr(icalfile, method)(*args)


@pytest.mark.parametrize("engine", ["icalendar", "ical"])
def test_icalfile_empty_keywords(engine):
    icalfile = IcalFile(EXAMPLE, engine=engine)
    icalfile.read()
    filtered_events = icalfile.filter_summary([])
    assert filtered_events == []
    assert icalfile.nevents() == 0


@pytest.mark.parametrize(
    "method, args",
    [
        ("nevents", ()),
        ("filter_summary", (["test"],)),
        ("clean_events", ()),
        ("normalize_vtimezone", ()),
        ("write", ("unused.ics",)),
    ],
)
def test_unsupported_engine_after_load(method, args):
    icalfile = IcalFile(EXAMPLE, engine="invalid")
    icalfile._calendar = object()

    with pytest.raises(ValueError, match="Unsupported engine"):
        getattr(icalfile, method)(*args)


def test_normalize_to_full_minutes():
    assert IcalFile.normalize_to_full_minutes(timedelta(minutes=4, seconds=29)) == timedelta(minutes=4)
    assert IcalFile.normalize_to_full_minutes(timedelta(minutes=4, seconds=31)) == timedelta(minutes=5)


def test_normalize_vtimezone():
    offset_from = SimpleNamespace(td=timedelta(hours=1, seconds=20))
    offset_to = SimpleNamespace(td=timedelta(hours=2, seconds=40))
    transition = {"TZOFFSETFROM": offset_from, "TZOFFSETTO": offset_to}
    timezone = SimpleNamespace(subcomponents=[transition])

    icalfile = IcalFile(EXAMPLE, verbose=False)
    icalfile._calendar = SimpleNamespace(walk=lambda name: [timezone] if name == "VTIMEZONE" else [])
    icalfile.normalize_vtimezone()

    assert offset_from.td == timedelta(hours=1)
    assert offset_to.td == timedelta(hours=2, minutes=1)
