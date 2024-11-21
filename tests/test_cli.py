from icalreporting._cli import icalcheck

def test_icalcheck_noarg(capsys):
    check = icalcheck([])
    captured = capsys.readouterr()
    assert "usage: icalcheck <filename>" in captured.out
    assert not check

def test_icalcheck_nofile(capsys):
    try:
        check = icalcheck(["examples/bad_file.ics"])
    except FileNotFoundError:
        pass
    captured = capsys.readouterr()
    assert "not found" in captured.out
    assert not check

def test_icalcheck(capsys):
    check = icalcheck(["examples/example_variations.ics"])
    captured = capsys.readouterr()
    assert "number of events" in captured.out
    assert "successfully using icalendar" in captured.out
    assert "successfully using ical" in captured.out
    assert check

