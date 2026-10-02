"""Keep the security guard's persisted state (block ledger, evidence log) out of the real home
directory while testing: a test that touched ~/.scrapamoja would put test noise into the
evidence a person reads with ``python -m src.security evidence``."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_security_state(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRAPAMOJA_SECURITY_DIR", str(tmp_path / "security"))
    monkeypatch.setenv("SCRAPAMOJA_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("SCRAPAMOJA_SNAPSHOT_DIR", str(tmp_path / "snapshots"))
