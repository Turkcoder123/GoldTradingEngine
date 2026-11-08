"""Tests for the monthly CSV read side: tail, head, headers and gaps."""

import datetime as dt
import pathlib

from src.core import csvfile, storage
from src.shared import config

START = dt.datetime(2026, 11, 6, 21, 55, tzinfo=dt.timezone.utc)


def bar(offset_minutes=0):
    moment = START + dt.timedelta(minutes=offset_minutes)
    return [int(moment.timestamp() * 1000), 1, 1, 1, 1, 1]


def month_file(data_dir, when=START, side=config.SIDE_BID):
    """Path object of the monthly CSV a bar of `when` belongs to."""
    return pathlib.Path(config.month_path(str(data_dir), when, side))


def test_month_files_lists_only_the_requested_side(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0)], config.SIDE_BID)
    storage.append_rows(str(tmp_path), [bar(1)], config.SIDE_ASK)
    names = [pathlib.Path(path).name
             for path in csvfile.month_files(str(tmp_path))]
    assert names == ["xauusd_1m_2026-11.csv"]


def test_tail_and_head_return_the_stored_range(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0), bar(1), bar(2)])
    path = month_file(tmp_path)
    assert csvfile.head_first_ms(str(path)) == bar(0)[0]
    assert csvfile.tail_last_ms(str(path)) == bar(2)[0]


def test_missing_files_report_zero(tmp_path):
    missing = month_file(tmp_path)
    assert csvfile.tail_last_ms(str(missing)) == 0
    assert csvfile.head_first_ms(str(missing)) == 0
    assert csvfile.header_ok(str(missing)) is True


def test_last_stored_ms_reads_the_newest_month(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0)])
    later = dt.datetime(2026, 12, 1, 0, 5, tzinfo=dt.timezone.utc)
    later_ms = int(later.timestamp() * 1000)
    storage.append_rows(str(tmp_path), [[later_ms, 1, 1, 1, 1, 1]])
    assert csvfile.last_stored_ms(str(tmp_path)) == later_ms


def test_newest_and_oldest_ms_span_several_months(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0)])
    later = dt.datetime(2026, 12, 1, 0, 5, tzinfo=dt.timezone.utc)
    later_ms = int(later.timestamp() * 1000)
    storage.append_rows(str(tmp_path), [[later_ms, 1, 1, 1, 1, 1]])
    paths = csvfile.month_files(str(tmp_path))
    assert csvfile.newest_ms(paths) == later_ms
    assert csvfile.oldest_ms(paths) == bar(0)[0]


def test_empty_directory_holds_no_data(tmp_path):
    assert csvfile.month_files(str(tmp_path)) == []
    assert csvfile.last_stored_ms(str(tmp_path)) == 0
    assert csvfile.newest_ms([]) == 0
    assert csvfile.oldest_ms([]) == 0


def test_header_ok_rejects_another_header(tmp_path):
    path = month_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("wrong,header\r\n", encoding=config.ENCODING)
    assert csvfile.header_ok(str(path)) is False


def test_ensure_clean_tail_drops_an_unterminated_last_line(tmp_path):
    path = month_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.HEADER + "\r\n2026-11-06 21:55:00,1,1,1,1,1\r\n"
                    "2026-11-06 21:56:00,2,2", encoding=config.ENCODING)
    removed = csvfile.ensure_clean_tail(str(path))
    assert removed > 0
    assert path.read_bytes().endswith(b"\r\n")


def test_ensure_clean_tail_leaves_a_clean_file_untouched(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0)])
    path = month_file(tmp_path)
    before = path.read_bytes()
    assert csvfile.ensure_clean_tail(str(path)) == 0
    assert path.read_bytes() == before


def test_gap_report_counts_missing_minutes(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0), bar(1), bar(5)])
    assert csvfile.gap_report(str(month_file(tmp_path))) == {
        "gaps": 1, "missing_minutes": 3, "largest_gap_minutes": 3}


def test_gap_report_is_empty_for_continuous_data(tmp_path):
    storage.append_rows(str(tmp_path), [bar(0), bar(1), bar(2)])
    assert csvfile.gap_report(str(month_file(tmp_path)))["gaps"] == 0
