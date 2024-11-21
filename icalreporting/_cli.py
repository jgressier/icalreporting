import sys
from icalreporting.icaltools import IcalFile

def _parseargs(argv, helpmsg=""):
    try:
        if argv is None:
            argv = sys.argv[1:] # mimic argparse
        filename = argv[0]
    except IndexError:
        print(helpmsg)
        return True, argv
    return False, argv

def icalcheck(argv=None): # argv for tests
    error, argv = _parseargs(argv, helpmsg="usage: icalcheck <filename>")
    if error:
        return not error
    filename = argv[0]
    _default_engine = 'icalendar'
    if _default_engine not in IcalFile._engines:
        raise NotImplementedError(f"{_default_engine} engine not available")
    # some info/stats/check with default engine
    print(f"> checking ICAL file: {filename}")
    file = IcalFile(filename, engine=_default_engine, verbose=False)
    try:
        file.read()
    except FileNotFoundError as e:
        print(f"Error reading file: {e}")
        return False
    print(f". number of events: {file.nevents()}")
    # check all engine can read file
    print("> check all reader engines")
    for engine in IcalFile._engines:
        print(f"- engine: {engine}")
        file = IcalFile(filename, engine=engine, verbose=False)
        try:
            file.read()
        except Exception as e:
            print(f"Error reading file with engine {engine}: {e}")
            error = True
    print("> done")      
    return not error # for pytest

def icalclean(argv=None):
    error, argv = _parseargs(argv, helpmsg="usage: icalcheck <filename>")
    if error:
        return not error
    filename = argv[0]
    file = IcalFile(filename, engine='icalendar')
    try:
        file.read()
    except FileNotFoundError as e:
        print(f"Error reading file: {e}")
        return False
    print(f"- number of events: {file.nevents()}")
    print(f"- normalizing timezones if necessary")
    file.normalize_vtimezone()
    print(f"- cleaning useless fields")
    file.clean_events()
    file.write(file._filename.with_suffix('.cleaned.ics'))
    print("> done")      
    return not error # for pytest
