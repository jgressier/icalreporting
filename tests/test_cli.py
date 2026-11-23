from pathlib import Path
import shutil
import sys

import pytest

from icalreporting._cli import icalcheck, icalclean, icalindividual, icalproject
from icalreporting.icaltools import IcalFile


EXAMPLE = Path("examples/example_variations.ics")


@pytest.mark.parametrize(
    "command, usage",
    [(icalcheck, "usage: icalcheck"), (icalclean, "usage: icalclean")],
)
def test_noarg(command, usage, capsys):
    check = command([])
    captured = capsys.readouterr()
    assert usage in captured.out
    assert not check


@pytest.mark.parametrize("command", [icalcheck, icalclean])
def test_nofile(command, capsys):
    check = command(["examples/bad_file.ics"])
    captured = capsys.readouterr()
    assert "not found" in captured.out
    assert not check


def test_icalcheck(capsys):
    check = icalcheck([str(EXAMPLE)])
    captured = capsys.readouterr()
    assert "number of events" in captured.out
    assert "successfully using icalendar" in captured.out
    assert "successfully using ical" in captured.out
    assert check


def test_icalcheck_uses_sys_argv(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["icalcheck", str(EXAMPLE)])
    assert icalcheck()


def test_icalcheck_reports_reader_failure(monkeypatch, capsys):
    monkeypatch.setattr(IcalFile, "_engines", ["icalendar", "invalid"])

    assert not icalcheck([str(EXAMPLE)])
    assert "Unsupported engine: invalid" in capsys.readouterr().out


def test_icalclean(tmp_path):
    source = tmp_path / "calendar.ics"
    shutil.copyfile(EXAMPLE, source)

    assert icalclean([str(source)])
    output = source.with_suffix(".cleaned.ics")
    assert output.exists()

    cleaned = IcalFile(output, verbose=False)
    cleaned.read()
    assert cleaned.nevents() == 7


def test_icalproject(tmp_path):
    output = tmp_path / "project.xlsx"

    assert icalproject(["examples/projectA", str(output), "--start", "2023-01-01", "--end", "2023-12-31"])
    assert output.exists()


def test_icalindividual(tmp_path):
    source = tmp_path / "individual.ics"
    source.write_text(
        """BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:event\nDTSTART:20240108T080000\nDTEND:20240108T090000\nSUMMARY:A/X work\nEND:VEVENT\nEND:VCALENDAR\n""",
        encoding="utf-8",
    )
    output = tmp_path / "individual.xlsx"

    assert icalindividual([str(tmp_path), str(output), "--start", "2024-01-01", "--end", "2024-01-31"])
    assert output.exists()
