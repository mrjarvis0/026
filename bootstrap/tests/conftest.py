"""Tests must never touch the live pause-flags file (bootstrap.consume writes it by default)."""
import pytest

from bootstrap import risk_flags


@pytest.fixture(autouse=True)
def _isolated_flags_file(tmp_path, monkeypatch):
    monkeypatch.setattr(risk_flags, "FLAGS_FILE", tmp_path / "isolated" / "pause_flags.json")
