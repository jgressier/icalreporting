import pytest
from icalreporting.icaltools import IcalFile
from pathlib import Path

def test_icalfile_init():
    icalfile = IcalFile('examples/example_variations.ics')
    # test default engine
    assert icalfile._engine == 'icalendar'
    assert icalfile._filename == Path('examples/example_variations.ics')
    # without read, calendar should be None
    assert icalfile._calendar is None

def test_icalfile_read_icalendar():
    icalfile = IcalFile('examples/example_variations.ics', engine='icalendar')
    icalfile.read()
    assert icalfile._calendar is not None
    assert icalfile._engine == 'icalendar'
    assert icalfile.nevents() == 7

def test_icalfile_read_ical():
    icalfile = IcalFile('examples/example_variations.ics', engine='ical')
    icalfile.read()
    assert icalfile._calendar is not None
    assert icalfile._engine == 'ical'
    assert icalfile.nevents() == 7

@pytest.mark.parametrize("engine", ['icalendar', 'ical'])
def test_icalfile_filter_summary(engine):
    icalfile = IcalFile('examples/example_variations.ics', engine=engine)
    icalfile.read()
    keywords = ['team']
    filtered_events = icalfile.filter_summary(keywords)
    assert len(filtered_events) == 2
    assert icalfile.nevents() == 2

@pytest.mark.parametrize("engine", ['icalendar', 'ical'])
def test_icalfile_write(engine):
    icalfile = IcalFile('examples/example_variations.ics', engine=engine)
    icalfile.read()
    icalfile.write('output.ics')
    assert Path('output.ics').exists()

def test_icalfile_invalid_engine():
    with pytest.raises(ValueError):
        icalfile = IcalFile('examples/example_variations.ics', engine='invalid')
        icalfile.read()

def test_icalfile_calendar_not_loaded():
    icalfile = IcalFile('examples/example_variations.ics')
    with pytest.raises(ValueError):
        icalfile.filter_summary(['test'])

def test_icalfile_empty_keywords():
    icalfile = IcalFile('examples/example_variations.ics')
    icalfile.read()
    keywords = []
    filtered_events = icalfile.filter_summary(keywords)
    assert len(filtered_events) == 0