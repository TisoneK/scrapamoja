"""Selector unit tests must not share persisted state: the threshold manager used to read and write
one ``data/thresholds.json`` for every instance, so each run saw the previous run's thresholds."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_thresholds_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRAPAMOJA_THRESHOLDS_FILE", str(tmp_path / "thresholds.json"))
