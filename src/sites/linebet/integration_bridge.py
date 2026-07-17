"""
Integration bridge for the Linebet site template.

This is a thin subclass of :class:`FullIntegrationBridge` that exists
mainly for framework-compliance — the quotes-style template (the
closest analogue to Linebet's hybrid pattern) does not use a bridge,
but github/wikipedia do, and the framework's compliance validator
expects one to be present when a template registers itself with the
registry.

The bridge owns:

* A reference to the YAML selector loader (so selectors can be hot-reloaded).
* A reference to :class:`LinebetExtractionRules` (so the framework's
  generic "extraction rule setup" code path has something to call).
* The Linebet-specific error-pattern table (rate-limit / 403 / 5xx
  recovery hints) consumed by the framework's error handler.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.sites.base.template.integration_bridge import FullIntegrationBridge
from src.sites.base.template.selector_loader import FileSystemSelectorLoader

from .config import API_URL_PATTERNS, SITE_DOMAIN, SUPPORTED_DOMAINS
from .extraction.rules import LinebetExtractionRules

logger = logging.getLogger(__name__)


class LinebetIntegrationBridge(FullIntegrationBridge):
    """Linebet-specific integration bridge."""

    def __init__(
        self,
        template_name: str,
        selector_engine: Any,
        page: Any,
        selectors_directory: Optional[str] = None,
        extraction_configs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            template_name=template_name,
            selector_engine=selector_engine,
            page=page,
            selector_configs={},
            extraction_configs=extraction_configs or {},
            **kwargs,
        )

        self.selectors_directory = selectors_directory or str(
            Path(__file__).parent / "selectors"
        )
        self.extraction_configs = extraction_configs or {}

        self.linebet_selector_loader = FileSystemSelectorLoader(
            template_name=template_name,
            selector_engine=selector_engine,
            selectors_directory=self.selectors_directory,
        )
        self.linebet_extraction_rules = LinebetExtractionRules()

        self.linebet_integration_status: Dict[str, Any] = {
            "selectors_loaded": False,
            "extraction_rules_setup": False,
            "framework_components_connected": False,
            "last_integration_check": None,
        }

        self.linebet_error_patterns: Dict[str, Dict[str, Any]] = {
            "rate_limit": {
                "pattern": "429|rate limit|too many requests",
                "recovery": "wait_and_retry",
                "wait_time": 10,
            },
            "forbidden": {
                "pattern": "403|forbidden|cloudflare",
                "recovery": "restart_browser_session",
            },
            "not_found": {
                "pattern": "404|not found",
                "recovery": "skip_item",
            },
            "server_error": {
                "pattern": "500|502|503|504",
                "recovery": "retry_with_backoff",
            },
        }

        logger.info("LinebetIntegrationBridge initialised for %s", template_name)

    async def _get_selector_configurations(self) -> Dict[str, Any]:
        """Load selectors from the Linebet selectors directory."""
        try:
            await self.linebet_selector_loader.load_site_selectors("linebet")
            loaded = self.linebet_selector_loader.get_loaded_selectors() \
                if hasattr(self.linebet_selector_loader, "get_loaded_selectors") else []
            return {name: {"name": name} for name in loaded}
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load Linebet selectors: %s", exc)
            return {}

    async def _get_extraction_rule_configurations(self) -> Dict[str, Any]:
        try:
            return self.linebet_extraction_rules.get_all_rule_configs()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to get Linebet extraction rules: %s", exc)
            return {}

    async def _setup_single_rule_set(self, rule_set_name: str, config: Dict[str, Any]) -> bool:
        try:
            return await self.linebet_extraction_rules.setup_rule_set(rule_set_name, config)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to set up Linebet rule set %s: %s", rule_set_name, exc)
            return False

    async def _finalize_integration(self) -> bool:
        self.linebet_integration_status.update(
            {
                "selectors_loaded": self.selector_count > 0,
                "extraction_rules_setup": self.extraction_rule_count > 0,
                "framework_components_connected": True,
                "last_integration_check": datetime.now().isoformat(),
            }
        )
        logger.info("Linebet integration finalised: %s", self.linebet_integration_status)
        return True

    def get_linebet_integration_status(self) -> Dict[str, Any]:
        base = self.get_integration_status() if hasattr(super(), "get_integration_status") else {}
        base.update(
            {
                "linebet_integration_status": self.linebet_integration_status.copy(),
                "selectors_directory": self.selectors_directory,
                "api_url_patterns": list(API_URL_PATTERNS),
                "supported_domains": list(SUPPORTED_DOMAINS),
                "site_domain": SITE_DOMAIN,
                "error_patterns": list(self.linebet_error_patterns.keys()),
            }
        )
        return base
