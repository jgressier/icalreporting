# icalreporting

[![PyPI version](https://img.shields.io/pypi/v/icalreporting.svg?style=flat)](https://pypi.org/project/icalreporting)
[![Python versions](https://img.shields.io/pypi/pyversions/icalreporting.svg?style=flat)](https://pypi.org/project/icalreporting)
[![Coverage](https://img.shields.io/codecov/c/github/jgressier/icalreporting.svg?style=flat)](https://codecov.io/gh/jgressier/icalreporting)

`icalreporting` converts iCalendar (`.ics`) files into pandas-based activity reports and Excel
workbooks. It expands recurring events and treats each ICS filename stem as a project member.

## Installation

Requires Python 3.9 or later.

```bash
pip install --upgrade icalreporting
```

## Project report

Place one ICS file per member in a directory. Work-package tags such as `WP2` are read from
event summaries.

```python
from icalreporting.reporting import Project

project = Project(
    name="Big Project",
    folder="calendars",
    start="2023-01-01",
    end="2023-12-31",
)
project.load_ics()
project.workbook().save("report.xlsx")
```

The workbook contains a global summary, member details, and monthly work-package totals.
All-day events are reported as 8-hour working days starting at 09:00.

`Hyperplanning` provides the same workflow for course calendars, grouped by course and
teaching type.

## Individual weekly report

`IndividualReporting` expects one calendar whose summaries follow
`SECTOR/SUBSECTOR optional comment`.

```python
from icalreporting.reporting import IndividualReporting

report = IndividualReporting("My activity", "examples/indiv-reporting")
report.load_ics()  # overlaps are corrected by shortening the first event
report.workbook().save("individual-report.xlsx")
```

Weeks run Sunday–Saturday. The workbook puts totals first, groups detail columns by sector then
subsector, and lists excluded malformed summaries in an `Unclassified` tab. It also reports hours
outside Monday–Friday 07:00–19:00. 

## Command line

```bash
icalcheck calendar.ics
icalclean calendar.ics  # writes calendar.cleaned.ics
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

Released under the MIT License.
