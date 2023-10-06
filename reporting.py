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
from icsts import read_ics
import pandas as pd
from pathlib import Path
import openpyxl as xl
from openpyxl.utils.dataframe import dataframe_to_rows


def ical_to_dframe(filename):
    return read_ics(str(filename))

class Project():
    def __init__(self, name: str, folder = None):
        self._name = name
        self._folder = name if folder is None else folder
        print(f"> init project {self._name} in folder {self._folder}")

    def load_ics(self):
        framedict = {}
        #print(Path(self._folder), Path(self._folder).exists(), Path(self._folder).is_dir())
        #print(list(Path(self._folder).glob("*.ics")))
        for filename in list(Path(self._folder).glob("*.ics")):
            print(f"- reading {filename}")
            framedict[filename.stem] = ical_to_dframe(filename)
            framedict[filename.stem]["Member"] = filename.stem # file name without path nor extension
        self._dframe = pd.concat(tuple(framedict.values()))
        self._set_wp(default="NOWP")
        self._clean_wp()

    def members(self):
        return set(self._dframe["Member"])

    def work_packages(self):
        return set(self._dframe["WP"])

    def _df_to_tab(self, wb: xl.Workbook, df, title=None):
        ws = wb.create_sheet(title=title)
        for row in dataframe_to_rows(df, header=True):
            ws.append(row)
        return ws

    def _df_slot(self, start:str, end: str):
        df = self._dframe
        slot = df[df["date"]>=start]
        slot = slot[slot["date"]<=end]
        return slot

    def _set_wp(self, default=None):
        rewp = re.compile(r"WP[0-9]*[A-Z]*")
        self._dframe["WP"] = self._dframe["name"].apply(lambda s: rewp.findall(s))
        self._dframe["WP"] = self._dframe["WP"].apply(lambda wplist: wplist[0] if wplist else default)

    def _clean_wp(self):
        rewp = re.compile(r"WP. *-* *")
        self._dframe["name"] = self._dframe["name"].apply(lambda s: rewp.sub("", s))
        return
    
    def filter(self, start:str, end: str):
        self._dframe = self._df_slot(start, end)
        
    def add_tabdetail_member(self, wb, member: str):
        df = self._dframe[self._dframe["Member"] == member].loc[:,["date", "duration", "WP", "name"]]
        ws = self._df_to_tab(wb, df, member)
        ws.delete_cols(1)
        ws.delete_rows(2)
        return ws
    
    def add_tab_workpackage(self, wb, wp: str):
        dfwp = self._dframe[self._dframe["WP"] == wp].loc[:,["date", "Member", "duration", "WP", "name", "year", "month"]]
        dfwp["YearMonth"] = dfwp.year.map(str)+"-"+dfwp.month.map(str)
        dfpiv = dfwp.pivot_table(values="duration", index="Member", columns="YearMonth", aggfunc="sum").fillna(0)
        ws = self._df_to_tab(wb, dfpiv, wp)
        ws.delete_rows(2)
        return ws

    def add_tab_allworkpackages(self, wb):
        df = self._dframe.pivot_table(values="duration", index="Member", columns="WP", aggfunc="sum").fillna(0)
        ws = self._df_to_tab(wb, df, "Synthèse")
        ws.delete_rows(2)

    def workbook(self)-> xl.Workbook:
        print("> create workbook")
        wb = xl.Workbook()
        ws_empty = wb.active
        print("- create global worksheet")
        self.add_tab_allworkpackages(wb)
        for member in self.members():
            print(f"- create member worksheet {member}")
            self.add_tabdetail_member(wb, member)
        for wp in self.work_packages():
            if wp is not None:
                print(f"- create WP worksheet {wp}")
                self.add_tab_workpackage(wb, wp)
        wb.remove(ws_empty)
        return wb


if __name__ == "__main__":
    prj = Project(name="mambo", folder="projetA")
    prj.load_ics() # lecture des .ics
    prj.filter(start="2023-01-01", end="2023-12-31") # filtre des dates
    wb = prj.workbook() # création du tableur
    wb.save("projetA.xlsx") # sauvegarde du fichier