"""Fixtures shared by the whole test suite (no network, no real data)."""

from __future__ import annotations

import os

import pytest

from src.shared import config


@pytest.fixture
def write_month():
    """Writes a monthly 1-minute CSV shaped exactly like the keeper's output."""

    def write(folder, name, rows):
        path = os.path.join(str(folder), name)
        os.makedirs(str(folder), exist_ok=True)
        with open(path, "w", encoding=config.ENCODING, newline="") as handle:
            handle.write(config.HEADER + "\n")
            for row in rows:
                handle.write(",".join(str(value) for value in row) + "\n")
        return path

    return write


@pytest.fixture
def write_cot():
    """Writes a stored COT report with the columns the exports carry."""

    def write(folder, report, year, rows):
        target = os.path.join(str(folder), "cot")
        os.makedirs(target, exist_ok=True)
        if report == "legacy":
            header = ("market,date,open_interest,noncomm_long,noncomm_short,"
                      "noncomm_spread,traders_long,traders_short,net")
        else:
            header = ("market,date,open_interest,managed_money_long,"
                      "managed_money_short,producer_long,producer_short,"
                      "swap_long,swap_short,net")
        path = os.path.join(target, f"cot_{report}_gold_{year}.csv")
        with open(path, "w", encoding=config.ENCODING, newline="") as handle:
            handle.write(header + "\n")
            for row in rows:
                handle.write(",".join(str(value) for value in row) + "\n")
        return path

    return write


@pytest.fixture
def write_fred():
    """Writes a stored FRED series as date,value rows."""

    def write(folder, series_id, rows):
        target = os.path.join(str(folder), "fred")
        os.makedirs(target, exist_ok=True)
        path = os.path.join(target, f"{series_id}.csv")
        with open(path, "w", encoding=config.ENCODING, newline="") as handle:
            handle.write("date,value\n")
            for row in rows:
                handle.write(",".join(str(value) for value in row) + "\n")
        return path

    return write
