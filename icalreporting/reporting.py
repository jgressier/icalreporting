"""reporting module

This module uses an ical loader package to fill a pandas database which is parsed to generate a workbook and worksheets

The difficulty may be to handle recurrent events.

note..:
    existing ical loading packages
    - ixsts (local, non pip) from N. Garcia-Rosa
    - icalendar
    - icalevents (fork of icalendar)
    - ics-py
    - ical (handle recurring events)
"""
import re
import smtplib
import warnings
from datetime import date, datetime, time, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from ical.calendar_stream import IcsCalendarStream
import pandas as pd
from pathlib import Path
import openpyxl as xl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

_default_startdate = "2020-01-01"
_default_enddate = "2030-01-01"


def _comparable_datetime(value):
    """Return a timezone-independent value suitable for ordering calendar dates."""
    if not isinstance(value, datetime):
        return datetime.combine(value, time.min)
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def ical_to_dframe(filename: Path, startdate: datetime, enddate: datetime):
    """read a file in ICAL format and create events between 2 dates
    can handle recurrent events

    Args:
        filename (Path): path name of ICAL file
        startdate (datetime): starting date for events
        enddate (datetime): ending date (included) for events

    Returns:
        DataFrame: event dates, duration, summary, description, begin/end, and all-day status
    """
    with filename.open() as ics_file:
        calendar = IcsCalendarStream.calendar_from_ics(ics_file.read())
    return pd.DataFrame(
        [
            {
                "date": event.dtstart,
                "year": event.dtstart.year,
                "month": event.dtstart.month,
                "h_begin": event.dtstart.time() if isinstance(event.dtstart, datetime) else time(9),
                "duration": (
                    (event.dtend - event.dtstart).total_seconds() / 3600.0
                    if isinstance(event.dtstart, datetime)
                    else (event.dtend - event.dtstart).days * 8.0
                ),
                "name": event.summary,
                "description": event.description,
                "begin": event.dtstart,
                "end": event.dtend,
                "all_day": not isinstance(event.dtstart, datetime),
            }
            for event in calendar.timeline.included(startdate, enddate)
        ]
    )


class IcalList():
    _ObjName = "Ical List"

    def __init__(self, name: str, folder=None, start: str = _default_startdate, end: str = _default_enddate):
        self._name = name
        self._folder = name if folder is None else folder
        self._start = datetime.fromisoformat(start)
        self._end = datetime.fromisoformat(end) + timedelta(days=1)
        print(f"> init {self._ObjName} {self._name} in folder {self._folder}")
        print(f"    will include {self._start.date()} to {self._end.date()} (not included)")

    def load_ics(self):
        """load ICS files and create pandas dataframe associated to member"""
        framedict = {}
        filelist = list(Path(self._folder).glob("*.ics"))
        for filename in filelist:
            print(f"- reading {filename}")
            framedict[filename.stem] = ical_to_dframe(filename, self._start, self._end)
            framedict[filename.stem]["Member"] = filename.stem  # file name without path nor extension
        if len(filelist) == 0:
            raise FileNotFoundError("no *.ics file found")
        self._dframe = pd.concat(tuple(framedict.values()), ignore_index=True)
        self._autoparse()
        self.clean()

    def _autoparse(self):
        pass

    def clean(self):
        pass

    def filter(self, start: str, end: str):
        """replace DataFrame with selected dates"""
        self._dframe = self._df_slot(start, end)

    def _df_slot(self, start: str, end: str):
        slot = self._dframe[self._dframe["date"] >= start]
        return slot[slot["date"] <= end]

    def members(self):
        """returns set (unordered list) of members"""
        return set(self._dframe["Member"])

    def check_overlaps(self, mode="warn"):
        """Find overlapping events and optionally shorten the first event.

        Args:
            mode: ``"warn"`` reports overlaps without changing events. ``"fix"``
                moves the end of the first event to the beginning of the
                second and updates its duration.

        Returns:
            DataFrame: one row per detected pair of overlapping events.
        """
        if mode not in {"warn", "fix"}:
            raise ValueError("overlap mode must be 'warn' or 'fix'")

        columns = [
            "Member",
            "first_index",
            "second_index",
            "first_name",
            "second_name",
            "first_begin",
            "old_end",
            "second_begin",
            "overlap_hours",
            "corrected",
            "new_end",
        ]
        conflicts = []
        for member, member_events in self._dframe.groupby("Member", sort=True):
            ordered = member_events.assign(
                _begin_cmp=member_events["begin"].map(_comparable_datetime),
                _end_cmp=member_events["end"].map(_comparable_datetime),
            ).sort_values(["_begin_cmp", "_end_cmp"])
            rows = list(ordered.iterrows())

            for position, (first_index, first) in enumerate(rows):
                first_begin = first["_begin_cmp"]
                first_end = first["_end_cmp"]
                for second_index, second in rows[position + 1:]:
                    second_begin = second["_begin_cmp"]
                    if second_begin >= first_end:
                        break

                    overlap = min(first_end, second["_end_cmp"]) - second_begin
                    can_fix = mode == "fix"
                    if can_fix:
                        # An all-day event ends at midnight of its exclusive
                        # end date.  Truncating it to the date of the next
                        # event therefore keeps only the preceding full days.
                        new_end = (
                            second["begin"].date()
                            if first["all_day"] and isinstance(second["begin"], datetime)
                            else second["begin"]
                        )
                    else:
                        new_end = None
                    conflicts.append(
                        {
                            "Member": member,
                            "first_index": first_index,
                            "second_index": second_index,
                            "first_name": first["name"],
                            "second_name": second["name"],
                            "first_begin": first["begin"],
                            "old_end": first["end"],
                            "second_begin": second["begin"],
                            "overlap_hours": overlap.total_seconds() / 3600.0,
                            "corrected": can_fix,
                            "new_end": new_end,
                        }
                    )

                    if can_fix:
                        self._dframe.at[first_index, "end"] = new_end
                        new_end_cmp = _comparable_datetime(new_end)
                        if first["all_day"]:
                            duration = max(
                                0.0, (new_end_cmp.date() - first_begin.date()).days * 8.0
                            )
                        else:
                            duration = max(
                                0.0, (new_end_cmp - first_begin).total_seconds() / 3600.0
                            )
                        self._dframe.at[first_index, "duration"] = duration
                        first_end = new_end_cmp
                        break

        result = pd.DataFrame(conflicts, columns=columns)
        if mode == "warn" and not result.empty:
            warnings.warn(
                f"{len(result)} overlapping event pair(s) found",
                UserWarning,
                stacklevel=2,
            )
        return result


class Project(IcalList):
    """Class Project, can read ICAL files, define tags and create worksheet 
    """

    _ObjName = "Project"
    _WP_model = r"WP[0-9.]*[A-Z]?"

    def __init__(self, name: str, folder=None, start: str = _default_startdate, end: str = _default_enddate, default_WP="No_WP"):
        super().__init__(name, folder, start, end)
        self._default_WP = default_WP

    def _autoparse(self):
        self._set_wp(default=self._default_WP)

    def clean(self):
        self._clean_wp()

    def work_packages(self):
        """returns set (unordered list) of Work Packages"""
        return set(self._dframe["WP"])

    def _df_to_tab(self, wb: xl.Workbook, df, title=None):
        ws = wb.create_sheet(title=title)
        for row in dataframe_to_rows(df, header=True):
            ws.append(row)
        return ws

    def _set_wp(self, default=None):
        """set WP properties using regexp in event name"""
        rewp = re.compile(self._WP_model)
        self._dframe["WP"] = self._dframe["name"].apply(lambda s: rewp.findall(s))
        self._dframe["WP"] = self._dframe["WP"].apply(lambda wplist: wplist[0] if wplist else default)

    def _clean_wp(self):
        rewp = re.compile(self._WP_model + r". *-* *")
        self._dframe["name"] = self._dframe["name"].apply(lambda s: rewp.sub("", s))
        return

    def add_tabdetail_member(self, wb, member: str):
        df = self._dframe[self._dframe["Member"] == member].loc[:, ["date", "duration", "WP", "name"]]
        df["date"] = df["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
        ws = self._df_to_tab(wb, df, member)
        ws.delete_cols(1)
        ws.delete_rows(2)
        return ws

    def add_tab_workpackage(self, wb, wp: str):
        dfwp = self._dframe[self._dframe["WP"] == wp].loc[
            :, ["date", "Member", "duration", "WP", "name", "year", "month"]
        ]
        monthformat = lambda m : f"{m:02}"
        dfwp["YearMonth"] = dfwp.year.map(str) + "-" + dfwp.month.map(monthformat)
        dfpiv = dfwp.pivot_table(
            values="duration", index="Member", columns="YearMonth", aggfunc="sum"
        ).fillna(0)
        ws = self._df_to_tab(wb, dfpiv, wp)
        ws.delete_rows(2)
        return ws

    def add_tab_allworkpackages(self, wb):
        df = self._dframe.pivot_table(values="duration", index="Member", columns="WP", aggfunc="sum")
        ws = self._df_to_tab(wb, df, "Synthèse")
        ws.delete_rows(2)

    def workbook(self) -> xl.Workbook:
        print("> create workbook")
        wb = xl.Workbook()
        ws_empty = wb.active
        print("- create global worksheet")
        self.add_tab_allworkpackages(wb)
        for member in self.members():
            print(f"- create member worksheet {member}")
            self.add_tabdetail_member(wb, member)
        for wp in sorted(self.work_packages()):
            if wp is not None:
                print(f"- create WP worksheet {wp}")
                self.add_tab_workpackage(wb, wp)
        wb.remove(ws_empty)
        return wb

class Hyperplanning(IcalList):
    """Class Hyperplanning, can read ICAL files, define tags and create worksheet 
    """

    _ObjName = "Hyperplanning"
    _course_model = r"^[0-9a-zA-Z-_]* - "

    def __init__(self, name: str, folder=None, start: str = _default_startdate, end: str = _default_enddate, default_course="No_course"):
        super().__init__(name, folder, start, end)
        self._default_course = default_course

    def _autoparse(self):
        self._set_course()
        self._set_type()

    def clean(self):
        self._clean_course()
        self._clean_type()

    def courses(self):
        """returns set (unordered list) of Work Packages"""
        return set(self._dframe["Course"])

    def _df_to_tab(self, wb: xl.Workbook, df, title=None):
        ws = wb.create_sheet(title=title)
        for row in dataframe_to_rows(df, header=True):
            ws.append(row)
        return ws

    def _set_course(self, default="unknown"):
        """set Course properties using regexp in event name"""
        rewp = re.compile(self._course_model)
        self._dframe["Course"] = self._dframe["name"].apply(lambda s: rewp.findall(s))
        self._dframe["Course"] = self._dframe["Course"].apply(lambda wplist: wplist[0][:-3] if wplist else default)

    def _clean_course(self):
        rewp = re.compile(self._course_model)
        self._dframe["name"] = self._dframe["name"].apply(lambda s: rewp.sub("", s))
        return

    def _set_type(self, default="unknown"):
        """set course type (Type) properties using regexp in event name"""
        rewp = re.compile(" - [a-zA-Z\\*]*$")
        self._dframe["CourseType"] = self._dframe["name"].apply(lambda s: rewp.findall(s))
        self._dframe["CourseType"] = self._dframe["CourseType"].apply(lambda wplist: wplist[0][3:] if wplist else default)

    def _clean_type(self):
        rewp = re.compile(" - [a-zA-Z\\*]*$")
        self._dframe["name"] = self._dframe["name"].apply(lambda s: rewp.sub("", s))
        return

    def add_tabdetail_member(self, wb, member: str):
        df = self._dframe[self._dframe["Member"] == member].loc[:, ["date", "duration", "Course", "CourseType", "name"]]
        df["date"] = df["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
        ws = self._df_to_tab(wb, df, member)
        ws.delete_cols(1)
        ws.delete_rows(2)
        return ws

    def add_tab_course(self, wb, course: str):
        dfwp = self._dframe[self._dframe["Course"] == course].loc[
            :, ["date", "Member", "duration", "Course", "CourseType", "name", "year", "month"]
        ]
        dfpiv = dfwp.pivot_table(
            values="duration", index="Member", columns="CourseType", aggfunc="sum"
        ).fillna(0)
        ws = self._df_to_tab(wb, dfpiv, course)
        ws.delete_rows(2)
        return ws

    def add_tab_allcourses(self, wb):
        df = self._dframe.pivot_table(values="duration", index="CourseType", columns="Course", aggfunc="sum")
        ws = self._df_to_tab(wb, df, "Synthèse")
        ws.delete_rows(2)

    def workbook(self) -> xl.Workbook:
        print("> create workbook")
        wb = xl.Workbook()
        ws_empty = wb.active
        print("- create global worksheet")
        self.add_tab_allcourses(wb)
        for member in self.members():
            print(f"- create member worksheet {member}")
            self.add_tabdetail_member(wb, member)
            #self.add_tabsumup_member(wb, member)
        # for course in sorted(self.courses()):
        #     if course is not None:
        #         print(f"- create course worksheet {wp}")
        #         self.add_tab_course(wb, wp)
        wb.remove(ws_empty)
        return wb


class IndividualReporting(IcalList):
    """Weekly activity reporting from one individual calendar."""

    _ObjName = "Individual reporting"
    _unclassified = "UNCLASSIFIED"
    _normal_start = time(7)
    _normal_end = time(19)

    def __init__(
        self,
        name: str,
        folder=None,
        start: str = _default_startdate,
        end: str = _default_enddate,
        timezone_name="Europe/Paris",
    ):
        super().__init__(name, folder, start, end)
        self._timezone = ZoneInfo(timezone_name)
        self._overlaps = pd.DataFrame()

    @staticmethod
    def _parse_summary(summary):
        if summary is None or (not isinstance(summary, str) and pd.isna(summary)):
            value = ""
        else:
            value = str(summary).strip()
        sector, separator, remainder = value.partition("/")
        if not separator or not sector.strip() or not remainder.strip():
            return IndividualReporting._unclassified, IndividualReporting._unclassified, value
        subsector, _, comment = remainder.strip().partition(" ")
        return sector.strip(), subsector.strip(), comment.strip()

    def _autoparse(self):
        parsed = self._dframe["name"].map(self._parse_summary)
        self._dframe[["Sector", "Subsector", "Comment"]] = pd.DataFrame(
            parsed.tolist(), index=self._dframe.index
        )
        self._dframe["Category"] = self._dframe["Sector"] + "/" + self._dframe["Subsector"]

    def clean(self):
        self._dframe = (
            self._dframe.assign(_sort_begin=self._dframe["begin"].map(_comparable_datetime))
            .sort_values("_sort_begin")
            .drop(columns="_sort_begin")
            .reset_index(drop=True)
        )

    def load_ics(self, overlap_mode="fix"):
        """Load exactly one ICS file and correct event overlaps by default."""
        filelist = list(Path(self._folder).glob("*.ics"))
        if len(filelist) != 1:
            raise ValueError(
                f"individual reporting expects exactly one ICS file; found {len(filelist)}"
            )
        super().load_ics()
        self._overlaps = self.check_overlaps(mode=overlap_mode)

    def _local_datetime(self, value, default_time=time.min):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=self._timezone)
            return value.astimezone(self._timezone)
        return datetime.combine(value, default_time, tzinfo=self._timezone)

    def _event_segments(self, event):
        """Yield local daily work segments for an event."""
        if event["all_day"]:
            current_day = event["begin"]
            end_day = event["end"]
            while current_day < end_day:
                yield (
                    self._local_datetime(current_day, time(9)),
                    self._local_datetime(current_day, time(17)),
                )
                current_day += timedelta(days=1)
            return

        current = self._local_datetime(event["begin"])
        event_end = self._local_datetime(event["end"])
        while current < event_end:
            next_day = datetime.combine(
                current.date() + timedelta(days=1), time.min, tzinfo=self._timezone
            )
            segment_end = min(event_end, next_day)
            yield current, segment_end
            current = segment_end

    def _outside_normal_hours(self, start, end):
        duration = (end - start).total_seconds() / 3600.0
        if start.weekday() >= 5:
            return duration
        normal_start = datetime.combine(start.date(), self._normal_start, tzinfo=self._timezone)
        normal_end = datetime.combine(start.date(), self._normal_end, tzinfo=self._timezone)
        inside = max(
            0.0,
            (min(end, normal_end) - max(start, normal_start)).total_seconds() / 3600.0,
        )
        return duration - inside

    def _range_boundary(self, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return self._local_datetime(value)
        if isinstance(value, date):
            return self._local_datetime(value)
        return self._local_datetime(datetime.fromisoformat(value))

    @staticmethod
    def _week_start(day):
        """Return the Sunday that starts the reporting week containing *day*."""
        return day - timedelta(days=(day.weekday() + 1) % 7)

    def unclassified_events(self):
        """Return events whose summary cannot be parsed as ``sector/subsector``."""
        result = self._dframe.loc[
            self._dframe["Sector"] == self._unclassified,
            ["begin", "end", "duration", "name", "Comment"],
        ].copy()
        return (
            result.assign(_sort_begin=result["begin"].map(_comparable_datetime))
            .sort_values("_sort_begin")
            .drop(columns="_sort_begin")
            .reset_index(drop=True)
        )

    def weekly_report(self, by="subsector", start=None, end=None):
        """Return weekly hours by sector/subsector or by sector only."""
        if by not in {"subsector", "sector"}:
            raise ValueError("weekly report grouping must be 'subsector' or 'sector'")

        range_start = self._range_boundary(start)
        range_end = self._range_boundary(end)
        records = []
        for _, event in self._dframe.iterrows():
            if event["Sector"] == self._unclassified:
                continue
            category = event["Sector"] if by == "sector" else event["Category"]
            for segment_start, segment_end in self._event_segments(event):
                if range_start is not None:
                    segment_start = max(segment_start, range_start)
                if range_end is not None:
                    segment_end = min(segment_end, range_end)
                if segment_start >= segment_end:
                    continue
                week_start = self._week_start(segment_start.date())
                records.append(
                    {
                        "Week": week_start.isoformat(),
                        "Category": category,
                        "Duration": (segment_end - segment_start).total_seconds() / 3600.0,
                        "Off hours": self._outside_normal_hours(
                            segment_start, segment_end
                        ),
                    }
                )

        if records:
            detail = pd.DataFrame(records)
            categories = detail.pivot_table(
                values="Duration", index="Week", columns="Category", aggfunc="sum", fill_value=0
            )
            totals = detail.groupby("Week").agg(
                Total=("Duration", "sum"),
                **{"Off hours": ("Off hours", "sum")},
            )
            report = totals.join(categories)
        else:
            report = pd.DataFrame(columns=["Total", "Off hours"])
            report.index.name = "Week"

        if range_start is not None and range_end is not None:
            first_sunday = self._week_start(range_start.date())
            weeks = []
            current = first_sunday
            while current < range_end.date():
                weeks.append(current.isoformat())
                current += timedelta(days=7)
            report = report.reindex(weeks, fill_value=0)
            report.index.name = "Week"

        return report.round(2)

    @staticmethod
    def _add_dataframe_sheet(wb, dataframe, title):
        ws = wb.create_sheet(title=title)
        for row in dataframe_to_rows(dataframe, index=False, header=True):
            ws.append(row)
        ws.freeze_panes = "A2"
        return ws

    @staticmethod
    def _excel_value(value):
        return value.isoformat() if hasattr(value, "isoformat") else value

    def _add_weekly_sheet(self, wb, report, title, details=False):
        """Add either a sector summary or a sector/subsector detail worksheet."""
        ws = wb.create_sheet(title=title)
        header_fill = PatternFill("solid", fgColor="1F4E78")
        total_fill = PatternFill("solid", fgColor="FFF2CC")
        sector_total_fill = PatternFill("solid", fgColor="FCE4D6")
        outside_fill = PatternFill("solid", fgColor="E7E6E6")
        header_font = Font(color="FFFFFF", bold=True)
        centered = Alignment(horizontal="center", vertical="center", wrap_text=True)

        fixed_headers = [
            ("Week", header_fill),
            ("Monday", header_fill),
            ("Total", total_fill),
            ("Off hours", outside_fill),
        ]
        for column, (title, fill) in enumerate(fixed_headers, start=1):
            ws.merge_cells(start_row=1, start_column=column, end_row=2, end_column=column)
            cell = ws.cell(1, column, title)
            cell.fill = fill
            cell.font = header_font if column <= 2 else Font(bold=True)
            cell.alignment = centered

        category_columns = [
            column for column in report.columns
            if column not in {"Total", "Off hours"}
        ]
        column = 5
        grouped = {}
        if details:
            for category in category_columns:
                sector, subsector = category.split("/", maxsplit=1)
                grouped.setdefault(sector, []).append((subsector, category))

            for sector in sorted(grouped):
                entries = sorted(grouped[sector])
                start_column = column
                for subsector, _ in entries:
                    cell = ws.cell(2, column, subsector)
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = centered
                    column += 1
                cell = ws.cell(2, column, "Total")
                cell.fill = sector_total_fill
                cell.font = Font(bold=True)
                cell.alignment = centered
                column += 1
                ws.merge_cells(
                    start_row=1, start_column=start_column, end_row=1, end_column=column - 1
                )
                cell = ws.cell(1, start_column, sector)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = centered
        else:
            for sector in sorted(category_columns):
                ws.merge_cells(start_row=1, start_column=column, end_row=2, end_column=column)
                cell = ws.cell(1, column, sector)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = centered
                column += 1

        for row_number, (week, values) in enumerate(report.iterrows(), start=3):
            week_start = date.fromisoformat(week)
            monday = week_start + timedelta(days=1)
            ws.cell(row_number, 1, f"W{monday.isocalendar().week:02d}")
            monday_cell = ws.cell(row_number, 2, monday)
            monday_cell.number_format = "dd/mm/yyyy"
            for col_number, label in ((3, "Total"), (4, "Off hours")):
                cell = ws.cell(row_number, col_number, float(values[label]))
                cell.number_format = "0.00"
                cell.fill = total_fill if col_number == 3 else outside_fill

            column = 5
            if details:
                for sector in sorted(grouped):
                    sector_total = 0.0
                    for _, category in sorted(grouped[sector]):
                        value = float(values[category])
                        cell = ws.cell(row_number, column, value)
                        cell.number_format = "0.00"
                        sector_total += value
                        column += 1
                    cell = ws.cell(row_number, column, sector_total)
                    cell.number_format = "0.00"
                    cell.fill = sector_total_fill
                    column += 1
            else:
                for sector in sorted(category_columns):
                    cell = ws.cell(row_number, column, float(values[sector]))
                    cell.number_format = "0.00"
                    column += 1

        for row in ws.iter_rows(min_row=1, max_row=2):
            for cell in row:
                cell.alignment = centered
        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 11
        ws.column_dimensions["C"].width = 9
        ws.column_dimensions["D"].width = 13
        for col_number in range(5, column):
            ws.column_dimensions[xl.utils.get_column_letter(col_number)].width = 9
        ws.freeze_panes = "E3"
        return ws

    def workbook(self):
        """Create sector summary, sector detail, and control worksheets."""
        wb = xl.Workbook()
        wb.remove(wb.active)
        self._add_weekly_sheet(wb, self.weekly_report(by="sector"), "Weekly")
        self._add_weekly_sheet(wb, self.weekly_report(), "Weekly details", details=True)

        unclassified = self.unclassified_events().copy()
        for column in ["begin", "end"]:
            unclassified[column] = unclassified[column].map(self._excel_value)
        self._add_dataframe_sheet(wb, unclassified, "Unclassified")

        overlaps = self._overlaps.copy()
        for column in ["first_begin", "old_end", "second_begin", "new_end"]:
            if column in overlaps:
                overlaps[column] = overlaps[column].map(self._excel_value)
        self._add_dataframe_sheet(wb, overlaps, "Overlaps")
        return wb

    def last_complete_weeks(self, as_of=None, weeks=4):
        """Return a sector-only report for the last complete Sunday-Saturday weeks."""
        if weeks <= 0:
            raise ValueError("weeks must be positive")
        reference = as_of or datetime.now(self._timezone)
        reference_date = reference.date() if isinstance(reference, datetime) else reference
        current_sunday = self._week_start(reference_date)
        first_sunday = current_sunday - timedelta(weeks=weeks)
        report = self.weekly_report(by="sector", start=first_sunday, end=current_sunday)
        report.index = pd.Index(
            [
                (date.fromisoformat(week_start) + timedelta(days=1)).isoformat()
                for week_start in report.index
            ],
            name="Monday",
        )
        return report

    def build_email(self, to_address, from_address, as_of=None):
        """Build the four-complete-week sector report email."""
        if not to_address or not from_address:
            raise ValueError("to_address and from_address are required")
        report = self.last_complete_weeks(as_of=as_of, weeks=4)
        message = EmailMessage()
        message["To"] = to_address
        message["From"] = from_address
        message["Subject"] = "Individual work report - last 4 complete weeks"
        message.set_content(
            "Work report for the last four complete weeks\n\n"
            + report.reset_index().to_string(index=False)
        )
        return message

    def send_email(
        self,
        to_address,
        from_address,
        smtp_host,
        smtp_port=587,
        username=None,
        password=None,
        use_tls=True,
        as_of=None,
        smtp_factory=smtplib.SMTP,
    ):
        """Send the four-complete-week sector report through SMTP."""
        if not smtp_host:
            raise ValueError("smtp_host is required")
        message = self.build_email(to_address, from_address, as_of=as_of)
        with smtp_factory(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            if username:
                server.login(username, password or "")
            server.send_message(message)
        return message


if __name__ == "__main__":
    prj = Project(name="mambo", folder="examples/projectA", start="2023-01-01", end="2024-01-01")
    prj.load_ics()  # lecture des .ics
    # prj.filter(start="2023-01-01", end="2023-12-31") # filtre des dates
    wb = prj.workbook()  # création du tableur
    wb.save("projetA.xlsx")  # sauvegarde du fichier
