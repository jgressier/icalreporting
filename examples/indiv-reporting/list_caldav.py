#!/usr/bin/env python3
"""List or download calendars available through the iCloud CalDAV account."""
import argparse
import copy
from getpass import getpass
import os
from pathlib import Path
import sys


def download_calendar(calendar, output):
    """Export VEVENT resources from a CalDAV calendar to one ICS file."""
    from icalendar import Calendar

    exported = Calendar()
    exported.add("prodid", "-//icalreporting//iCloud export//EN")
    exported.add("version", "2.0")
    event_count = 0
    for resource in calendar.objects(load_objects=True):
        if not resource.data:
            continue
        source = Calendar.from_ical(resource.data)
        for component in source.subcomponents:
            if component.name == "VEVENT":
                exported.add_component(copy.deepcopy(component))
                event_count += 1
    output.write_bytes(exported.to_ical())
    return event_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apple-id",
        default=os.getenv("ICLOUD_USERNAME"),
        help="Apple ID (or set ICLOUD_USERNAME)",
    )
    parser.add_argument(
        "--download",
        type=int,
        metavar="INDEX",
        help="download the calendar at this displayed index",
    )
    parser.add_argument(
        "--calendar-url",
        help="download this CalDAV calendar collection directly",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="output ICS file (required with --download)",
    )
    arguments = parser.parse_args()
    if not arguments.apple_id:
        parser.error("--apple-id or ICLOUD_USERNAME is required")
    if arguments.download is not None and arguments.calendar_url:
        parser.error("use either --download or --calendar-url")
    has_download_target = arguments.download is not None or arguments.calendar_url is not None
    if has_download_target != (arguments.output is not None):
        parser.error("--output is required with --download or --calendar-url")

    try:
        import caldav
    except ImportError:
        print("Install the optional dependency with: pip install caldav", file=sys.stderr)
        return 1

    password = os.getenv("ICLOUD_PASSWORD") or getpass("iCloud app-specific password: ")
    client_url = arguments.calendar_url or "https://caldav.icloud.com/.well-known/caldav"
    with caldav.DAVClient(
        url=client_url,
        username=arguments.apple_id,
        password=password,
        auth_type="basic",
    ) as client:
        if arguments.calendar_url:
            calendar = caldav.Calendar(client=client, url=client.url)
            count = download_calendar(calendar, arguments.output)
            print(f"Downloaded {count} event resource(s) to {arguments.output}")
            return 0
        calendars = list(client.principal().calendars())
        for number, calendar in enumerate(calendars):
            print(f"{number}: {calendar.name}")
            print(f"   {calendar.url}")
        if arguments.download is not None:
            if not 0 <= arguments.download < len(calendars):
                parser.error(f"calendar index must be between 0 and {len(calendars) - 1}")
            count = download_calendar(calendars[arguments.download], arguments.output)
            print(f"Downloaded {count} event resource(s) to {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
