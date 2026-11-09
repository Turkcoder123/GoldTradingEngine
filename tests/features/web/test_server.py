"""Tests for the HTTP surface: a real server on an ephemeral port."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from src.features.web import server
from src.shared import config

ROWS = [
    ("2026-11-06 23:00:00", 11, 12, 10, 11.5, 1),
    ("2026-11-06 23:59:00", 11.5, 12, 11, 11.9, 1),
]


@pytest.fixture
def base_url(tmp_path):
    """A dashboard server for an empty data directory, stopped afterwards."""
    handler = server.make_handler(
        server.Dashboard(str(tmp_path), ttl_seconds=1.0))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def get(url, expect=200):
    """(status, body bytes) of one request, failing on an unexpected code."""
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, body = exc.code, exc.read()
    assert status == expect, (status, body[:200])
    return status, body


def get_json(url, expect=200):
    """Parsed JSON body of one request."""
    _status, body = get(url, expect)
    return json.loads(body)


def test_page_is_served_with_the_labels_and_the_title(base_url):
    _status, body = get(base_url + "/")
    html = body.decode("utf-8")
    assert "<title>Gold Market Data Dashboard</title>" in html
    assert "{{" not in html
    assert 'id="dashboard-config"' in html


def test_overview_lists_every_series(base_url):
    body = get_json(base_url + "/api/overview")
    assert body["ok"] is True
    assert body["section"] == "overview"
    assert len(body["data"]["series"]) == len(config.SERIES)
    assert body["data"]["totals"]["files"] == 0
    assert body["version"]


def test_series_endpoint_serves_the_daily_bars(base_url, tmp_path,
                                                write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    body = get_json(base_url + "/api/series/xauusd?months=1")
    assert body["ok"] is True
    assert body["data"]["key"] == "xauusd"
    assert body["data"]["summary"]["bars"] == 2
    assert body["data"]["summary"]["last_close"] == 11.9


def test_an_unknown_series_is_a_client_error(base_url):
    body = get_json(base_url + "/api/series/nope", expect=400)
    assert body["ok"] is False
    assert "nope" in body["error"]


def test_cot_and_macro_answer_with_an_empty_data_directory(base_url):
    cot = get_json(base_url + "/api/cot")
    assert cot["ok"] is True
    assert cot["data"]["reports"] == {}
    macro = get_json(base_url + "/api/macro")
    assert macro["ok"] is True
    assert macro["data"]["series"] == []


def test_the_smc_endpoint_answers_an_empty_window(base_url):
    body = get_json(base_url + "/api/smc/xauusd?months=1")
    assert body["ok"] is True
    assert body["section"] == "smc"
    assert body["data"]["timeframe"] == "1d"
    assert body["data"]["events"] == []
    assert body["data"]["bars"]["count"] == 0


def test_the_smc_endpoint_detects_the_structures_of_a_stored_file(
        base_url, tmp_path, write_month):
    rows = [(f"2026-11-{day:02d} 12:00:00", close, close + 1, close - 1,
             close + 0.5, 1)
            for day, close in enumerate([10, 11, 12, 13, 12, 11, 10, 9, 8,
                                         9, 10, 11], start=1)]
    write_month(tmp_path, "xauusd_1m_2026-11.csv", rows)
    body = get_json(base_url + "/api/smc/xauusd?months=1")
    assert body["data"]["bars"]["count"] == 12
    assert body["data"]["summary"]


def test_an_unknown_smc_series_is_a_client_error(base_url):
    body = get_json(base_url + "/api/smc/nope", expect=400)
    assert body["ok"] is False
    assert "nope" in body["error"]


def test_the_months_parameter_is_clamped(base_url, tmp_path, write_month):
    write_month(tmp_path, "xauusd_1m_2026-11.csv", ROWS)
    body = get_json(base_url + "/api/series/xauusd?months=999")
    assert body["data"]["months_requested"] == server.MAX_MONTHS
    body = get_json(base_url + "/api/series/xauusd?months=nonsense")
    assert body["data"]["months_requested"] == server.DEFAULT_MONTHS


def test_static_assets_carry_their_content_type(base_url):
    status, body = get(base_url + "/static/app.js")
    assert status == 200
    assert b"DashboardApp" in body
    _status, body = get(base_url + "/static/style.css")
    assert b"--gold" in body


def test_an_unknown_path_and_a_traversal_are_not_found(base_url):
    get(base_url + "/api/nothing", expect=404)
    get(base_url + "/static/%2e%2e/server.py", expect=404)


def test_refresh_drops_the_caches(base_url):
    body = get_json(base_url + "/api/refresh")
    assert body["ok"] is True
    assert body["data"]["refreshed"] is True


def test_the_favicon_request_is_answered_without_a_body(base_url):
    status, body = get(base_url + "/favicon.ico", expect=204)
    assert status == 204
    assert body == b""
