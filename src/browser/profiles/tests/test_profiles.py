"""Persistent browser profiles: bookkeeping, locking and launch arguments."""
import asyncio
import os

import pytest

from src.browser.profiles import ProfileError, ProfileInUse, ProfileManager


class FakeCtx:
    closed = False

    async def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self):
        self.calls = []
        self.ctx = FakeCtx()

    async def launch_persistent_context(self, user_data_dir, **kw):
        self.calls.append((user_data_dir, kw))
        return self.ctx


class FakePW:
    def __init__(self):
        self.chromium = FakeChromium()


def test_create_list_delete(tmp_path):
    pm = ProfileManager(tmp_path)
    assert pm.list() == []
    m = pm.get_or_create("linebet", notes="warmed by hand")
    assert pm.exists("linebet") and pm.data_dir("linebet").is_dir()
    assert pm.get_or_create("linebet").created_at == m.created_at          # idempotent
    assert [p.name for p in pm.list()] == ["linebet"]
    pm.delete("linebet")
    assert pm.list() == [] and not pm.exists("linebet")


@pytest.mark.parametrize("bad", ["", "../etc", "a/b", ".hidden", "x" * 65])
def test_invalid_names_rejected(tmp_path, bad):
    with pytest.raises(ProfileError):
        ProfileManager(tmp_path).get_or_create(bad)


def test_open_context_passes_profile_dir_and_options_and_closes(tmp_path):
    pm, pw = ProfileManager(tmp_path), FakePW()

    async def go():
        async with pm.open_context(pw, "p", headless=False, channel="chrome", stealth_args=True,
                                   proxy={"server": "http://h:1"},
                                   identity={"locale": "en-GB", "user_agent": None}) as ctx:
            assert ctx is pw.chromium.ctx and not ctx.closed
    asyncio.run(go())
    (path, kw), = pw.chromium.calls
    assert path == str(pm.data_dir("p"))
    assert kw["headless"] is False and kw["channel"] == "chrome" and kw["locale"] == "en-GB"
    assert "user_agent" not in kw                                           # None = browser's own
    assert "--disable-blink-features=AutomationControlled" in kw["args"]
    assert kw["ignore_default_args"] == ["--enable-automation"]
    assert pw.chromium.ctx.closed
    assert pm.get("p").uses == 1 and not (tmp_path / "p" / ".lock").exists()


def test_identity_is_stored_with_the_profile(tmp_path):
    pm = ProfileManager(tmp_path)
    pm.get_or_create("p", identity={"locale": "fr-FR"})
    pw = FakePW()

    async def go():
        async with pm.open_context(pw, "p"):
            pass
    asyncio.run(go())
    assert pw.chromium.calls[0][1]["locale"] == "fr-FR"


def test_profile_in_use_by_another_live_process_is_refused(tmp_path):
    pm = ProfileManager(tmp_path)
    pm.get_or_create("p")
    (tmp_path / "p" / ".lock").write_text(str(os.getppid()))                # a live pid that isn't us

    async def go():
        async with pm.open_context(FakePW(), "p"):
            pass
    with pytest.raises(ProfileInUse):
        asyncio.run(go())
    with pytest.raises(ProfileInUse):
        pm.delete("p")


def test_stale_lock_from_a_dead_process_is_taken_over(tmp_path):
    pm = ProfileManager(tmp_path)
    pm.get_or_create("p")
    (tmp_path / "p" / ".lock").write_text("999999")

    async def go():
        async with pm.open_context(FakePW(), "p"):
            pass
    asyncio.run(go())


def test_per_launch_identity_is_not_persisted(tmp_path):
    pm = ProfileManager(tmp_path)

    async def go(identity):
        pw = FakePW()
        async with pm.open_context(pw, "p", identity=identity):
            pass
        return pw.chromium.calls[0][1]
    assert asyncio.run(go({"user_agent": "UA-1"}))["user_agent"] == "UA-1"
    assert "user_agent" not in asyncio.run(go(None))          # a later tier must not inherit it


def test_warmup_proxy_from_env_keeps_credentials_out_of_argv(monkeypatch):
    from src.browser.profiles.__main__ import proxy_from_env
    monkeypatch.setenv("X_PROXY_URL", "http://h.example:1074")
    monkeypatch.setenv("X_PROXY_USER", "u")
    monkeypatch.setenv("X_PROXY_PASS", "p")
    assert proxy_from_env("X_PROXY_URL") == {"server": "http://h.example:1074",
                                             "username": "u", "password": "p"}
    monkeypatch.setenv("Y_URL", "http://a%40b:pw@h.example:9")        # creds embedded, url-encoded
    assert proxy_from_env("Y_URL") == {"server": "http://h.example:9", "username": "a@b", "password": "pw"}
    monkeypatch.delenv("NOPE", raising=False)
    with pytest.raises(ValueError):
        proxy_from_env("NOPE")
