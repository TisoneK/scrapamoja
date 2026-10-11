"""Tests for BaseExtractor._extract_time_info (src/.../base_extractor.py).

The method only touches ``element.query_selector`` / ``text_content`` and
``self.logger``, so it is exercised with lightweight fakes — no browser. The
point under test: a *live* match returns its stage (quarter/clock) from
``.event__stage``, where before it returned ``None``.
"""

from __future__ import annotations

import logging

from src.sites.flashscore.extractors.base_extractor import BaseExtractor


class _FakeNode:
    def __init__(self, text):
        self._text = text

    async def text_content(self):
        return self._text


class _FakeMatch:
    """Returns a node for whichever selector the extractor asks for."""

    def __init__(self, *, stage=None, time=None):
        self._stage = _FakeNode(stage) if stage is not None else None
        self._time = _FakeNode(time) if time is not None else None

    async def query_selector(self, selector):
        if "stage" in selector:
            return self._stage
        if "event__time" in selector:
            return self._time
        return None


class _Self:
    """Minimal stand-in carrying just the logger the method uses."""

    logger = logging.getLogger("test.base_extractor")


async def _time_info(match, status):
    return await BaseExtractor._extract_time_info(_Self(), match, status)


async def test_live_returns_stage_text():
    match = _FakeMatch(stage="Quarter 1\n7:32")
    assert await _time_info(match, "live") == "Quarter 1\n7:32"


async def test_live_without_stage_returns_none():
    match = _FakeMatch(stage=None, time="18:30")
    # No stage node, and the live branch must not fall back to .event__time.
    assert await _time_info(match, "live") is None


async def test_scheduled_returns_event_time():
    match = _FakeMatch(stage="Quarter 1", time="18:30")
    assert await _time_info(match, "scheduled") == "18:30"


async def test_finished_returns_event_time():
    match = _FakeMatch(time="Finished")
    assert await _time_info(match, "finished") == "Finished"
