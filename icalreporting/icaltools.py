from pathlib import Path
import importlib
from icalendar import Calendar
from ical.calendar_stream import IcsCalendarStream

class IcalFile:
    _engines = ['icalendar', 'ical']

    def __init__(self, filename, engine='icalendar'):
        self._engine = engine
        self._filename = Path(filename)
        self._calendar = None
        print(f"Initializing IcalFile with engine {engine} and file {filename}")

    def _read_icalendar(self):
        with self._filename.open('r') as icsfile:
            self._calendar = Calendar.from_ical(icsfile.read())
        print(len(self._calendar.subcomponents))
        # for item in self._calendar.walk('VALARM'):
        #     print(item)
        #     self._calendar.subcomponents.remove(item)
        # print(len(self._calendar.subcomponents))
        print("Calendar read successfully using icalendar")

    def _read_ical(self):
        with self._filename.open('r') as icsfile:
            self._calendar = IcsCalendarStream.calendar_from_ics(icsfile.read())
        print("Calendar read successfully using ical")

    def read(self):
        if self._engine == 'icalendar':
            self._read_icalendar()
        elif self._engine == 'ical':
            self._read_ical()
        else:
            raise ValueError(f"Unsupported engine: {self._engine}")

    def nevents(self):
        if self._calendar is None:
            raise ValueError("Calendar not loaded")
        if self._engine == 'icalendar':
            return len(self._calendar.subcomponents)
        elif self._engine == 'ical':
            return len(self._calendar.events)
        else:
            raise ValueError(f"Unsupported engine: {self._engine}")
        
    def filter_summary(self, keywords: list):
        if self._calendar is None:
            raise ValueError("Calendar not loaded")
        if self._engine == 'icalendar':
            events = self._calendar.walk('VEVENT')
            filtered_events = [event for event in events if any(key.lower() in event.get('SUMMARY').lower() for key in keywords)]
            print(len(self._calendar.subcomponents))
            for event in events:
                self._calendar.subcomponents.remove(event)
            print(len(self._calendar.subcomponents))
            for event in filtered_events:
                self._calendar.add_component(event)
            print(len(self._calendar.subcomponents))
        elif self._engine == 'ical':
            events = self._calendar.events
            filtered_events = [event for event in events if any(key.lower() in event.summary.lower() for key in keywords)]
            self._calendar.events = filtered_events
        else:
            raise ValueError(f"Unsupported engine: {self._engine}")
        print(f"Filtered {len(filtered_events)} events with keywords {keywords}")
        return filtered_events

    def clean_events(self):
        _useless_attributes = ['DESCRIPTION', 'TRANSP', '']
        if self._calendar is None:
            raise ValueError("Calendar not loaded")
        if self._engine == 'icalendar':
            self._calendar.walk('VEVENT').clear()
        elif self._engine == 'ical':
            self._calendar.events = []
        else:
            raise ValueError(f"Unsupported engine: {self._engine}")
        
    def write(self, filename):
        filename = Path(filename)
        if self._calendar is None:
            raise ValueError("Calendar not loaded")
        if self._engine == 'icalendar':
            with filename.open('wb') as icsfile:
                icsfile.write(self._calendar.to_ical())
        elif self._engine == 'ical':
            with filename.open('w') as icsfile:
                icsfile.write(IcsCalendarStream.calendar_to_ics(self._calendar))
        else:
            raise ValueError(f"Unsupported engine: {self._engine}")
        print(f"Calendar written successfully to {filename}")