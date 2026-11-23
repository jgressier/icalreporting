import argparse
import sys
from pathlib import Path

from icalreporting.reporting import IndividualReporting, Project
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
    error, argv = _parseargs(argv, helpmsg="usage: icalclean <filename>")
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


def _report_parser(prog, description, include_default_wp=False):
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument("folder", type=Path, help="folder containing ICS calendar files")
    parser.add_argument("output", type=Path, help="XLSX workbook to create")
    parser.add_argument("--start", default="2020-01-01", help="first included date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2030-01-01", help="last included date (YYYY-MM-DD)")
    if include_default_wp:
        parser.add_argument(
            "--default-wp",
            default="No_WP",
            help="work-package label for events without a WP tag (default: No_WP)",
        )
    return parser


def icalproject(argv=None):
    """Create a project XLSX workbook from ICS files in a folder."""
    parser = _report_parser(
        "icalproject",
        "Create a project XLSX workbook from one ICS file per member.",
        include_default_wp=True,
    )
    arguments = parser.parse_args(argv)
    project = Project(
        arguments.folder.name,
        folder=arguments.folder,
        start=arguments.start,
        end=arguments.end,
        default_WP=arguments.default_wp,
    )
    project.load_ics()
    project.workbook().save(arguments.output)
    print(f"Workbook written to {arguments.output}")
    return True


def icalindividual(argv=None):
    """Create an individual weekly XLSX workbook from one ICS file."""
    parser = _report_parser(
        "icalindividual",
        "Create an individual weekly XLSX workbook from exactly one ICS file.",
    )
    parser.add_argument("--timezone", default="Europe/Paris", help="IANA timezone (default: Europe/Paris)")
    arguments = parser.parse_args(argv)
    report = IndividualReporting(
        arguments.folder.name,
        folder=arguments.folder,
        start=arguments.start,
        end=arguments.end,
        timezone_name=arguments.timezone,
    )
    report.load_ics()
    report.workbook().save(arguments.output)
    print(f"Workbook written to {arguments.output}")
    print(f"Detected {len(report._overlaps)} overlapping event pair(s)")
    return True
