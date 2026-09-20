from pathlib import Path
import shutil
import sys

import pytest

from icalreporting._cli import icalcheck, icalclean
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
