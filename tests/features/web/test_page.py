"""Tests for the HTML shell and the static assets (LANG-4, MOD-2)."""

from __future__ import annotations

import json

from src.features.web import page


def test_render_page_fills_the_title_the_labels_and_the_version():
    template = ('<title>{{TITLE}}</title>'
                '<script id="labels">{{LABELS}}</script>'
                '<body data-version="{{VERSION}}">')
    html = page.render_page(template)
    assert "{{" not in html
    assert "<title>Gold Market Data Dashboard</title>" in html
    labels = json.loads(html.split('id="labels">')[1].split("</script>")[0])
    assert labels["app.title"] == "Gold Market Data Dashboard"
    assert 'data-version="' in html


def test_static_path_stays_inside_the_static_folder():
    assert page.static_path("app.js") is not None
    assert page.static_path("../server.py") is None
    assert page.static_path("../../../../etc/passwd") is None
    assert page.static_path("missing.js") is None


def test_static_body_serves_the_stylesheet():
    content_type, data = page.static_body("style.css")
    assert content_type.startswith("text/css")
    assert b"--gold" in data


def test_static_body_serves_javascript():
    content_type, data = page.static_body("app.js")
    assert content_type.startswith("text/javascript")
    assert b"DashboardApp" in data


def test_static_body_reports_a_missing_asset():
    assert page.static_body("missing.js") is None


def test_template_loads_every_module_the_page_needs():
    template = page.read_template()
    for name in ("chart_core.js", "chart_candle.js", "chart_smc.js",
                 "chart_line.js", "chart_bars.js", "sparkline.js", "dom.js",
                 "overview_panel.js", "price_panel.js", "smc_panel.js",
                 "cot_panel.js", "macro_panel.js", "alt_panel.js",
                 "runtime.js", "layout.js", "app.js"):
        assert "/static/" + name in template, name
    for name in ("style.css", "panels.css", "alt.css", "smc.css"):
        assert "/static/" + name in template, name
