import sys
from icalreporting.icaltools import IcalFile

def icalcheck(argv=None):
    error = False
    try:
        if argv is None:
            argv = sys.argv[1:] # mimic argparse
        filename = argv[0]
    except IndexError:
        print("usage: icalcheck <filename>")
        return False
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
