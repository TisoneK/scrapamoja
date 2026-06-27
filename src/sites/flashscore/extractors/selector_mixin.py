"""
Mixin providing timeout-protected YAML selector engine resolution.

The YAML selector engine can be slow (12-40s per resolve across multiple
strategies) and has historically exhibited hang-like behavior.  On Python
3.8, CancelledError inherited from Exception, so the engine's ``except
Exception`` handlers would swallow cancellation, making
``asyncio.wait_for`` timeouts ineffective.  On Python 3.12+,
CancelledError is BaseException and propagates through those handlers, so
plain ``asyncio.wait_for`` should work — but the engine's strategy
iteration is still inherently slow, and Playwright CDP operations may not
respond promptly to cancellation.

This mixin wraps calls in a separate asyncio.Task that can be force-
cancelled after the timeout expires, ensuring bounded execution time
regardless of Python version.
"""

import asyncio
from typing import Any, List, Optional


class SelectorEngineMixin:
    """Mixin that adds timeout-protected YAML selector engine helpers.

    Expects the host class to have:
    - ``self._selector_engine`` — the YAML selector engine (or None)
    - ``self.logger`` — a logger instance
    - ``self.scraper.page`` or ``self.page`` — a Playwright Page
    """

    async def _resolve_element(self, selector_name: str, parent=None) -> Optional[Any]:
        """Resolve a single element via YAML selector engine with 8-second timeout protection.

        Uses a separate asyncio.Task so that we can force-cancel if the
        selector engine takes too long.  The engine's strategy iteration
        (4+ strategies × 3-10s each) can take 12-40s, and on Python 3.8
        its ``except Exception`` handlers would swallow CancelledError.
        The force-cancel pattern ensures bounded execution on all versions.

        Args:
            selector_name: The ``id`` of a YAML selector definition.
            parent: Optional Playwright element to scope the search.  Falls
                back to the page when *None*.

        Returns:
            A Playwright ``ElementHandle`` or ``None``.
        """
        if self._selector_engine:
            try:
                page = getattr(self, 'page', None) or self.scraper.page
                search_target = parent or page
                task = asyncio.create_task(
                    self._selector_engine.find(search_target, selector_name)
                )
                try:
                    return await asyncio.wait_for(task, timeout=8.0)
                except asyncio.TimeoutError:
                    self.logger.debug(f"YAML selector '{selector_name}' timed out after 8s — force cancelling")
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
                    return None
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return None

    async def _resolve_elements(self, selector_name: str, parent=None) -> List[Any]:
        """Resolve multiple elements via YAML selector engine with 8-second timeout protection.

        Uses a separate asyncio.Task so that we can force-cancel if the
        selector engine takes too long (see _resolve_element for rationale).

        Args:
            selector_name: The ``id`` of a YAML selector definition.
            parent: Optional Playwright element to scope the search.

        Returns:
            A list of Playwright ``ElementHandle`` objects (may be empty).
        """
        if self._selector_engine:
            try:
                page = getattr(self, 'page', None) or self.scraper.page
                search_target = parent or page
                task = asyncio.create_task(
                    self._selector_engine.find_all(search_target, selector_name)
                )
                try:
                    elements = await asyncio.wait_for(task, timeout=8.0)
                    if elements:
                        return elements
                except asyncio.TimeoutError:
                    self.logger.debug(f"YAML selector '{selector_name}' timed out after 8s — force cancelling")
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
                    return []
            except Exception as e:
                self.logger.debug(f"YAML selector '{selector_name}' failed: {e}")
        return []

    async def _resolve_text(self, selector_name: str, parent=None) -> Optional[str]:
        """Resolve element text content via YAML selector engine.

        Args:
            selector_name: The ``id`` of a YAML selector definition.
            parent: Optional Playwright element to scope the search.

        Returns:
            Trimmed text content string or ``None``.
        """
        el = await self._resolve_element(selector_name, parent)
        if el:
            try:
                text = await el.text_content()
                return text.strip() if text else None
            except Exception as e:
                self.logger.debug(f"Text extraction for '{selector_name}' failed: {e}")
        return None
