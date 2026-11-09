"""Tests for the minimal `.env` reader (GIT-6, OPEN-6)."""

import os

from src.shared import envfile


def test_parse_reads_key_value_pairs_and_skips_comments():
    text = "\n# a comment\nTWELVE_DATA_API_KEY=abc123\n\nOTHER='quoted'\n"
    assert envfile.parse(text) == {"TWELVE_DATA_API_KEY": "abc123",
                                   "OTHER": "quoted"}


def test_parse_strips_the_export_prefix_and_double_quotes():
    assert envfile.parse('export API_KEY="secret"') == {"API_KEY": "secret"}


def test_parse_keeps_the_equals_sign_of_a_value():
    assert envfile.parse("TOKEN=a=b=c") == {"TOKEN": "a=b=c"}


def test_parse_ignores_lines_without_a_key():
    assert envfile.parse("=novalue\nNOEQUALS") == {}


def test_read_answers_an_empty_map_for_a_missing_file(tmp_path):
    assert envfile.read(str(tmp_path / "missing.env")) == {}


def test_load_never_overrides_an_exported_variable(monkeypatch, tmp_path):
    path = tmp_path / ".env"
    path.write_text("KEY_FROM_FILE=from-file\n", encoding="utf-8")
    monkeypatch.delenv("KEY_FROM_FILE", raising=False)
    envfile.load(str(path))
    assert os.environ["KEY_FROM_FILE"] == "from-file"
    monkeypatch.setenv("KEY_FROM_FILE", "from-shell")
    envfile.load(str(path))
    assert os.environ["KEY_FROM_FILE"] == "from-shell"
