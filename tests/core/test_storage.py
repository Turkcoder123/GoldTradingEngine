"""Tests for the monthly CSV write side: format, dedup and header rules."""

import datetime as dt
import pathlib

import pytest

from src.core import csvfile, storage
from src.shared import config

START = dt.datetime(2026, 11, 6, 21, 55, tzinfo=dt.timezone.utc)


def bar(offset_minutes=0, price=1.0):
    """One feed row: [ts_ms, open, high, low, close, volume]."""
    moment = START + dt.timedelta(minutes=offset_minutes)
    stamp = int(moment.timestamp() * 1000)
    return [stamp, price, price + 0.5, price - 0.5, price + 0.25, 10]


def read_lines(path):
    with open(path, "rb") as handle:
        raw = handle.read()
    return [line.decode(config.ENCODING)
            for line in raw.split(b"\r\n") if line.strip()]


def month_file(data_dir, when=START, side=config.SIDE_BID):
    """Path object of the monthly CSV a bar of `when` belongs to."""
    return pathlib.Path(config.month_path(str(data_dir), when, side))


def test_append_creates_one_header_and_crlf_rows(tmp_path):
    result = storage.append_rows(str(tmp_path), [bar(0), bar(1)])
    lines = read_lines(month_file(tmp_path))
    assert result.added == 2
    assert lines[0] == config.HEADER
    assert lines[1] == "2026-11-06 21:55:00,1.0,1.5,0.5,1.25,10"
    assert len(lines) == 3


def test_append_is_idempotent_for_stored_minutes(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0), bar(1)])
    result = storage.append_rows(str(tmp_path), [bar(0), bar(1)])
    assert (result.added, result.late, result.duplicates) == (0, 2, 0)
    assert len(read_lines(month_file(tmp_path))) == 3


def test_append_deduplicates_a_repeated_minute_inside_one_batch(tmp_path):
    result = storage.append_rows(str(tmp_path), [bar(0, 1.0), bar(0, 2.0)])
    assert (result.added, result.duplicates) == (1, 1)
    assert len(read_lines(month_file(tmp_path))) == 2


def test_append_sorts_rows_and_reports_the_newest_minute(tmp_path):
    result = storage.append_rows(str(tmp_path), [bar(2), bar(0), bar(1)])
    lines = read_lines(month_file(tmp_path))[1:]
    stamps = [line.split(",")[0] for line in lines]
    assert stamps == ["2026-11-06 21:55:00", "2026-11-06 21:56:00",
                      "2026-11-06 21:57:00"]
    assert result.newest == bar(2)[0]


def test_append_splits_rows_at_a_month_boundary(tmp_path):
    when = dt.datetime(2026, 10, 31, 23, 58, tzinfo=dt.timezone.utc)
    rows = [[int((when + dt.timedelta(minutes=step)).timestamp() * 1000),
             1, 1, 1, 1, 1] for step in range(4)]
    result = storage.append_rows(str(tmp_path), rows)
    assert result.added == 4
    assert sorted(result.files) == ["xauusd_1m_2026-10.csv",
                                   "xauusd_1m_2026-11.csv"]
    assert csvfile.tail_last_ms(month_file(tmp_path, when)) == rows[1][0]
    assert csvfile.head_first_ms(month_file(tmp_path, when)) == rows[0][0]


def test_append_refuses_a_file_with_another_header(tmp_path):
    path = month_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("time,o,h,l,c,v\r\n2026-11-06 21:55:00,1,1,1,1,1\r\n",
                    encoding=config.ENCODING)
    with pytest.raises(storage.StorageError):
        storage.append_rows(str(tmp_path), [bar(0)])


def test_append_after_a_partial_line_keeps_the_file_valid(tmp_path):
    path = month_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.HEADER + "\r\n2026-11-06 21:55:00,1,1,1,1,1\r\n"
                    "2026-11-06 21:56:00,2,2", encoding=config.ENCODING)
    result = storage.append_rows(str(tmp_path), [bar(1), bar(2)])
    lines = read_lines(path)
    assert result.added == 2
    assert len(lines) == 4
    assert lines[-1].startswith("2026-11-06 21:57:00")


def test_offer_sides_never_share_a_file(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0)], config.SIDE_BID)
    storage.append_rows(str(tmp_path), [bar(1)], config.SIDE_ASK)
    assert csvfile.last_stored_ms(str(tmp_path), config.SIDE_BID) == bar(0)[0]
    assert csvfile.last_stored_ms(str(tmp_path), config.SIDE_ASK) == bar(1)[0]


def test_write_rows_creates_the_parent_directory(tmp_path):
    target = tmp_path / "nested" / "deep" / "xauusd_1m_2026-11.csv"
    written = storage.write_rows(str(target), [bar(0)])
    assert written == 1
    assert target.exists()
