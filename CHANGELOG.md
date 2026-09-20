
## version 0.4.0 (unreleased)

- support all-day events as working days starting at 09:00, with 8 reported hours per day
- preserve actual start times and full durations for timed and multi-day events
- fix Hyperplanning course worksheet generation (`CourseType` column)
- correct the `icalclean` command usage message

## version 0.3.1 (2024/11/22)

- add the missing `icalendar` runtime dependency
- declare support for Python 3.13
- use Python 3.11 to build and publish the package

## version 0.3.0 (2024/11/13)

- `reporting.icaltools`: some tools using a less sensitive package icalendar
- new command line `icalcheck <file>`
- new command line `icalclean <file>`

## version 0.2.0 (2024/08/30)

- `reporting.Hyperplanning` class able to read ical and make worksheets with Hyperplanning calendars

## version 0.1.1 (2023/10/10)

- `reporting.Project` class able to read ical and make worksheets with reports
