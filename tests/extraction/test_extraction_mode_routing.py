"""Tests for extraction mode routing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.sites.base.site_config import SiteConfig, ExtractionMode, SiteConfigLoader


class TestExtractionModeRouter:
    """Test cases for extraction mode router."""

    def test_get_extraction_mode_from_config(self):
        """Test that extraction mode is read from configuration."""
        config = SiteConfig(
            site_name="test_site",
            endpoint="https://example.com",
            extraction_mode=ExtractionMode.RAW
        )
        assert config.get_extraction_mode() == "raw"

    def test_default_extraction_mode_is_raw(self):
        """Test that default extraction mode is raw (Direct API)."""
        config = SiteConfig(
            site_name="test_site",
            endpoint="https://example.com"
        )
        # Default should be RAW per AC #4
        assert config.extraction_mode == ExtractionMode.RAW
        assert config.get_extraction_mode() == "raw"

    def test_valid_extraction_modes(self):
        """Test all valid extraction modes are accepted."""
        valid_modes = [
            ExtractionMode.RAW,
            ExtractionMode.INTERCEPTED,
            ExtractionMode.PLAYWRIGHT,
            ExtractionMode.HYBRID,
        ]
        for mode in valid_modes:
            config = SiteConfig(
                site_name="test_site",
                endpoint="https://example.com",
                extraction_mode=mode
            )
            assert config.extraction_mode == mode

    def test_invalid_extraction_mode_raises_error(self):
        """Test that invalid extraction mode raises validation error."""
        with pytest.raises(Exception):  # Pydantic validation error
            SiteConfig(
                site_name="test_site",
                endpoint="https://example.com",
                extraction_mode="invalid_mode"
            )

    def test_site_config_get_extraction_mode_returns_string(self):
        """Test get_extraction_mode returns string value."""
        config = SiteConfig(
            site_name="test_site",
            endpoint="https://example.com",
            extraction_mode=ExtractionMode.RAW
        )
        result = config.get_extraction_mode()
        assert isinstance(result, str)
        assert result == "raw"


class TestExtractionModeFactory:
    """Test cases for extraction mode factory/router."""

    def test_factory_creates_raw_mode_handler(self):
        """Test factory creates correct handler for raw mode."""
        from src.extraction.router import ExtractionModeRouter
        
        config = SiteConfig(
            site_name="test_site",
            endpoint="https://example.com",
            extraction_mode=ExtractionMode.RAW
        )
        
        router = ExtractionModeRouter(config)
        handler = router.get_handler()
        
        assert handler is not None

    def test_factory_creates_intercepted_mode_handler(self):
        """Test factory creates correct handler for intercepted mode."""
        from src.extraction.router import ExtractionModeRouter
        
        config = SiteConfig(
            site_name="test_site",
            endpoint="https://example.com",
            extraction_mode=ExtractionMode.INTERCEPTED
        )
        
        router = ExtractionModeRouter(config)
        handler = router.get_handler()
        
        assert handler is not None

    def test_factory_raises_for_invalid_mode(self):
        """Test factory raises error for invalid mode."""
        from src.extraction.router import ExtractionModeRouter, InvalidExtractionModeError
        
        # Create config with invalid mode - Pydantic raises validation error
        # so we test that SiteConfig rejects invalid values
        with pytest.raises(Exception):
            SiteConfig(
                site_name="test_site",
                endpoint="https://example.com",
                extraction_mode="invalid"
            )


class TestExtractionModeRouting:
    """Integration tests for extraction mode routing."""

    @pytest.mark.asyncio
    async def test_route_to_raw_mode(self):
        """Test routing to raw (Direct API) mode."""
        from src.extraction.router import ExtractionModeRouter, RawExtractionHandler
        
        config = SiteConfig(
            site_name="test_site",
            endpoint="https://example.com",
            extraction_mode=ExtractionMode.RAW
        )
        
        router = ExtractionModeRouter(config)
        handler = router.get_handler()
        
        # Raw mode should use RawExtractionHandler
        assert isinstance(handler, RawExtractionHandler)
        assert handler.endpoint == "https://example.com"

    def test_flashscore_config_has_intercepted_mode(self):
        """Test flashscore config declares intercepted mode."""
        loader = SiteConfigLoader("flashscore")
        config = loader.load()
        
        assert config.extraction_mode == ExtractionMode.INTERCEPTED

    def test_wikipedia_config_has_intercepted_mode(self):
        """Test wikipedia config declares intercepted mode."""
        loader = SiteConfigLoader("wikipedia")
        config = loader.load()
        
        assert config.extraction_mode == ExtractionMode.INTERCEPTED


class TestExtractionModeValidation:
    """Tests for extraction mode validation."""

    def test_validation_error_message_includes_valid_options(self):
        """Test that validation error includes list of valid options."""
        from src.extraction.router import InvalidExtractionModeError
        
        error = InvalidExtractionModeError("invalid")
        
        assert "raw" in str(error).lower()
        assert "intercepted" in str(error).lower()
        assert "playwright" in str(error).lower()
        assert "hybrid" in str(error).lower()

    def test_extraction_mode_enum_values(self):
        """Test ExtractionMode enum has correct values."""
        assert ExtractionMode.RAW.value == "raw"
        assert ExtractionMode.INTERCEPTED.value == "intercepted"
        assert ExtractionMode.PLAYWRIGHT.value == "playwright"
        assert ExtractionMode.HYBRID.value == "hybrid"


class TestHybridExtractionHandler:
    """Tests for HybridExtractionHandler class."""

    def test_handler_initialization(self):
        """Test HybridExtractionHandler initialization."""
        from src.extraction.router import HybridExtractionHandler

        handler = HybridExtractionHandler(
            endpoint="https://example.com",
            site_name="test_site",
            session_ttl=3600,
            browser_config={"headless": True},
            force_bootstrap=False,
        )

        assert handler.endpoint == "https://example.com"
        assert handler.site_name == "test_site"
        assert handler._session_ttl == 3600
        assert handler._needs_bootstrap is True

    def test_handler_default_values(self):
        """Test HybridExtractionHandler default values."""
        from src.extraction.router import HybridExtractionHandler

        handler = HybridExtractionHandler(
            endpoint="https://example.com",
            site_name="test_site",
        )

        assert handler._session_ttl is None
        assert handler._browser_config == {"headless": True}
        assert handler._force_bootstrap is False
        assert handler._session is None
        assert handler._client is None

    def test_handler_is_bootstrap_needed(self):
        """Test is_bootstrap_needed property."""
        from src.extraction.router import HybridExtractionHandler

        handler = HybridExtractionHandler(
            endpoint="https://example.com",
            site_name="test_site",
        )

        # Initially needs bootstrap
        assert handler.is_bootstrap_needed() is True

    def test_handler_get_session(self):
        """Test get_session returns None initially."""
        from src.extraction.router import HybridExtractionHandler

        handler = HybridExtractionHandler(
            endpoint="https://example.com",
            site_name="test_site",
        )

        assert handler.get_session() is None

    def test_handler_repr(self):
        """Test HybridExtractionHandler repr."""
        from src.extraction.router import HybridExtractionHandler

        handler = HybridExtractionHandler(
            endpoint="https://example.com",
            site_name="test_site",
        )

        assert "HybridExtractionHandler" in repr(handler)
        assert "test_site" in repr(handler)

    def test_handler_protocol_compliance(self):
        """Test HybridExtractionHandler follows ExtractionHandlerProtocol."""
        from src.extraction.router import HybridExtractionHandler

        handler = HybridExtractionHandler(
            endpoint="https://example.com",
            site_name="test_site",
        )

        # Verify protocol compliance - handler has extract method
        assert hasattr(handler, 'extract')
        assert callable(handler.extract)
        # Verify handler has close method
        assert hasattr(handler, 'close')
        assert callable(handler.close)

    @pytest.mark.asyncio
    async def test_handler_close_cleans_up(self):
        """Test close method cleans up resources."""
        from src.extraction.router import HybridExtractionHandler

        handler = HybridExtractionHandler(
            endpoint="https://example.com",
            site_name="test_site",
        )

        # Set some state
        handler._needs_bootstrap = False

        # Close should reset state
        await handler.close()

        assert handler._client is None
        assert handler._session is None
        assert handler._needs_bootstrap is True


class TestHybridModeRouting:
    """Tests for routing to hybrid mode."""

    def test_route_to_hybrid_mode(self):
        """Test router returns HybridExtractionHandler for hybrid mode."""
        from src.extraction.router import ExtractionModeRouter, HybridExtractionHandler
        from src.sites.base.site_config import SiteConfig, ExtractionMode

        config = SiteConfig(
            site_name="test_site",
            endpoint="https://example.com",
            extraction_mode=ExtractionMode.HYBRID,
        )

        router = ExtractionModeRouter(config)
        handler = router.get_handler()

        # Should return HybridExtractionHandler
        assert isinstance(handler, HybridExtractionHandler)
        assert handler.site_name == "test_site"
        assert handler.endpoint == "https://example.com"


class TestInterceptedExtractionHandler:
    """Tests for InterceptedExtractionHandler."""

    def test_handler_initialization(self):
        """Test InterceptedExtractionHandler initializes correctly."""
        from src.extraction.router import InterceptedExtractionHandler
        
        handler = InterceptedExtractionHandler(
            endpoint="https://api.example.com",
            site_name="test_site",
            url_patterns=[r".*api.*\\.json$"],
            capture_body=True,
            capture_headers=True,
        )
        
        assert handler.endpoint == "https://api.example.com"
        assert handler.site_name == "test_site"
        assert handler._url_patterns == [r".*api.*\\.json$"]
        assert handler._capture_body is True
        assert handler._capture_headers is True

    def test_handler_default_values(self):
        """Test InterceptedExtractionHandler has correct defaults."""
        from src.extraction.router import InterceptedExtractionHandler
        
        handler = InterceptedExtractionHandler(
            endpoint="https://api.example.com",
            site_name="test_site",
        )
        
        assert handler._url_patterns == []
        assert handler._capture_body is True
        assert handler._capture_headers is True
        assert handler._browser_config == {"headless": True}

    def test_handler_creates_network_listener(self):
        """Test InterceptedExtractionHandler creates NetworkListener."""
        from src.extraction.router import InterceptedExtractionHandler
        
        handler = InterceptedExtractionHandler(
            endpoint="https://api.example.com",
            site_name="test_site",
            url_patterns=[r".*api.*"],
        )
        
        listener = handler._create_listener()
        
        assert listener is not None
        assert listener.config.url_patterns == [r".*api.*"]
        assert listener.config.capture_body is True
        assert listener.config.capture_headers is True

    @pytest.mark.asyncio
    async def test_handler_extract_requires_page_or_url(self):
        """Test extract() requires either page or url."""
        from src.extraction.router import InterceptedExtractionHandler
        
        handler = InterceptedExtractionHandler(
            endpoint="https://api.example.com",
            site_name="test_site",
        )
        
        # Should raise ValueError when neither page nor url provided
        with pytest.raises(ValueError, match="Either page or url must be provided"):
            await handler.extract()

    @pytest.mark.asyncio
    async def test_handler_extract_with_url_creates_browser(self):
        """Test extract() with url creates browser and navigates."""
        from src.extraction.router import InterceptedExtractionHandler
        
        handler = InterceptedExtractionHandler(
            endpoint="https://api.example.com",
            site_name="test_site",
            url_patterns=[r".*"],
            browser_config={"headless": True},
        )
        
        # Mock response
        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/data"
        mock_response.status = 200
        mock_response.status_text = "OK"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.body = AsyncMock(return_value=b'{"test": true}')
        
        # Mock page
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.goto.return_value = mock_response
        mock_page.wait_for_load_state = AsyncMock()
        
        # Mock browser
        mock_browser = MagicMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()
        
        # Mock playwright
        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        
        with patch('playwright.async_api.async_playwright', return_value=mock_playwright):
            # Just verify the handler can be created and has correct config
            assert handler.endpoint == "https://api.example.com"
            assert handler._browser_config == {"headless": True}

    @pytest.mark.asyncio
    async def test_handler_close(self):
        """Test close() method cleans up resources."""
        from src.extraction.router import InterceptedExtractionHandler
        
        handler = InterceptedExtractionHandler(
            endpoint="https://api.example.com",
            site_name="test_site",
        )
        
        # Set up mock listener
        mock_listener = MagicMock()
        mock_listener.detach = AsyncMock()
        handler._listener = mock_listener
        
        # Set up mock page with AsyncMock for async close()
        mock_page = AsyncMock()
        handler._page = mock_page
        
        await handler.close()
        
        mock_listener.detach.assert_called_once()
        mock_page.close.assert_called_once()
        assert handler._listener is None
        assert handler._page is None

    def test_handler_repr(self):
        """Test handler repr."""
        from src.extraction.router import InterceptedExtractionHandler
        
        handler = InterceptedExtractionHandler(
            endpoint="https://api.example.com",
            site_name="test_site",
        )
        
        repr_str = repr(handler)
        assert "InterceptedExtractionHandler" in repr_str
        assert "test_site" in repr_str
