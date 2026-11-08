"""Tests for the VERSION reader (single source of truth, VER-3)."""

import pytest

from src.shared import config, version


def test_read_version_uses_the_project_version_file_by_default():
    with open(config.VERSION_FILE, "r", encoding=config.ENCODING) as handle:
        assert version.read_version() == handle.read().strip()


def test_read_version_accepts_a_pre_release_suffix(tmp_path):
    path = tmp_path / "VERSION"
    path.write_text("1.3.0-dev.2\n", encoding=config.ENCODING)
    assert version.read_version(str(path)) == "1.3.0-dev.2"


def test_read_version_rejects_a_missing_file(tmp_path):
    with pytest.raises(version.VersionError):
        version.read_version(str(tmp_path / "missing"))


def test_read_version_rejects_invalid_content(tmp_path):
    path = tmp_path / "VERSION"
    path.write_text("not a version\n", encoding=config.ENCODING)
    with pytest.raises(version.VersionError):
        version.read_version(str(path))
