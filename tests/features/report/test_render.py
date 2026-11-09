"""Tests for the text layout of the data report."""

from __future__ import annotations

from src.features.report import locale, render

DOCUMENT = {
    "version": "1.3.0",
    "generated_at": "2026-11-08 12:00:00",
    "data_dir": "/tmp/data",
    "totals": {"series": 1, "files": 1, "bars": 4, "size_mb": 0.01,
               "first_bar": "2026-11-05 21:58:00",
               "last_bar": "2026-11-06 23:59:00"},
    "prices": [{
        "key": "xauusd", "instrument": "XAU/USD", "frequency": "1 min",
        "files": 1, "size_mb": 0.01, "bars": 4, "days": 2,
        "first_bar": "2026-11-05 21:58:00",
        "last_bar": "2026-11-06 23:59:00",
        "first_close": 10.5, "last_close": 11.9,
        "day_change_pct": 10.19, "range_change_pct": 13.33, "age_minutes": 90,
    }],
    "cot": {"year": 2026, "years": [2026], "rows": [{
        "report": "legacy", "frequency": "weekly", "first_date": "2026-10-27",
        "last_date": "2026-11-03", "reports": 2, "open_interest": 1200,
        "net": 450, "net_share": 0.375, "weekly_change": 50,
        "trend_change": 120, "trend_weeks": 2,
    }]},
    "macro": [{
        "id": "DGS10", "label": "10-year Treasury yield", "unit": "percent",
        "frequency": "daily", "first_date": "2019-01-02",
        "last_date": "2026-11-05", "observations": 2, "value": 4.84,
        "date": "2026-11-05", "change": -0.06, "year_change": 3.84,
    }],
    "etf": [{
        "key": "gld", "label": "SPDR Gold Shares",
        "source": "SPDR Gold Shares historical archive (XLSX)", "rows": 5730,
        "first_date": "2004-11-18", "last_date": "2026-11-05",
        "tonnes": 1040.51,
    }],
    "volatility": [{
        "key": "GVZ", "label": "Cboe Gold ETF Volatility Index", "rows": 4309,
        "first_date": "2009-09-18", "last_date": "2026-11-06", "close": 25.97,
    }],
    "fed": {
        "rows": 6, "texts": 6, "first_date": "2026-10-07",
        "last_date": "2026-10-28", "chars": 63007,
        "kinds": {"speech": 2, "minutes": 1, "minutes_release": 2,
                  "statement": 1},
    },
    "rates": {
        "countries": {
            "US": {"label": "United States", "rows": 312,
                   "first_date": "2000-01-01", "last_date": "2026-09-01",
                   "latest": 1.25, "change_1y": -0.75},
            "DE": {"label": "Germany", "rows": 0, "first_date": None,
                   "last_date": None, "latest": None, "change_1y": None},
        },
        "world": {"median": 1.25, "date": "2026-09-01", "count": 1,
                  "min": 1.25, "max": 1.25, "points": []},
    },
}


def test_number_formats_without_trailing_zeros():
    assert render.number(4069.545) == "4,069.545"
    assert render.number(51.9) == "51.9"
    assert render.number(6748145.0) == "6,748,145"
    assert render.number(0.01, 2) == "0.01"
    assert render.number(None) == "-"


def test_percent_and_signed_values_keep_their_sign():
    assert render.percent(1.234) == "+1.23%"
    assert render.percent(-0.39) == "-0.39%"
    assert render.percent(None) == "-"
    assert render.signed(179548) == "+179,548"
    assert render.signed(-6903) == "-6,903"
    assert render.signed(0.73, 3) == "+0.730"
    assert render.signed(None) == "-"


def test_age_switches_units():
    assert render.age(0) == "-"
    assert render.age(90) == "90 min"
    assert render.age(44 * 60) == "44 h"
    assert render.age(72 * 60) == "3 d"


def test_table_right_aligns_a_column_of_numbers():
    lines = render.table(["A", "B"], [["x", "1"], ["y", "22"]])
    assert lines[0] == "A   B"
    assert set(lines[1]) <= {"-", " "}
    assert lines[2] == "x   1"
    assert lines[3] == "y  22"


def test_render_prints_every_section():
    text = render.render(DOCUMENT, locale.labels(), locale.notes())
    labels = locale.labels()
    for key in ("title", "prices.coverage.title", "prices.latest.title",
                "cot.title", "macro.title", "notes"):
        assert labels[key] in text, key
    assert "xauusd" in text
    assert "XAU/USD" in text
    assert "1 min" in text
    assert "11.9" in text
    assert "+10.19%" in text
    assert "37.5%" in text
    assert "+450" in text
    assert "10-year Treasury yield" in text
    assert "percent" in text
    assert "2026-11-08 12:00:00" in text


def test_render_is_ascii_and_newline_terminated():
    text = render.render(DOCUMENT, locale.labels(), locale.notes())
    assert text.isascii()
    assert text.endswith("\n")
    assert "{{" not in text


def test_render_prints_the_real_rate_section():
    text = render.render(DOCUMENT, locale.labels(), locale.notes())
    labels = locale.labels()
    assert labels["rates.title"] in text
    assert "United States" in text
    assert "+1.250" in text
    assert "-0.750" in text
    assert "world median +1.250 over 1 countries" in text
    assert "Germany" not in text


def test_render_prints_the_alternative_sections():
    text = render.render(DOCUMENT, locale.labels(), locale.notes())
    labels = locale.labels()
    for key in ("etf.title", "volatility.title", "fed.title"):
        assert labels[key] in text, key
    assert "1,040.51" in text
    assert "GVZ" in text
    assert "25.97" in text
    assert "speech" in text
    assert "6 documents" in text


def test_render_handles_an_empty_data_directory():
    document = {
        "version": "1.3.0", "generated_at": "2026-11-08 12:00:00",
        "data_dir": "/tmp/data",
        "totals": {"series": 0, "files": 0, "bars": 0, "size_mb": 0.0,
                   "first_bar": None, "last_bar": None},
        "prices": [], "cot": {"year": None, "years": [], "rows": []},
        "macro": [],
        "etf": [], "volatility": [],
        "fed": {"rows": 0, "texts": 0, "first_date": None, "last_date": None,
                "chars": 0, "kinds": {}},
        "rates": {"countries": {}, "world": {"median": None, "count": 0,
                                              "points": []}},
    }
    text = render.render(document, locale.labels(), locale.notes())
    assert locale.labels()["nothing"] in text
    assert text.isascii()


def test_notes_are_wrapped_to_a_readable_width():
    text = render.render(DOCUMENT, locale.labels(), locale.notes())
    assert max(len(line) for line in text.splitlines()) <= 120


def test_render_without_notes_leaves_the_legend_out():
    text = render.render(DOCUMENT, locale.labels())
    assert locale.labels()["notes"] not in text
