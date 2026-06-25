"""
Unit tests for site configuration loading.

Tests the YAML-based site configuration system from Story 3.1:
YAML Site Configuration
"""


import pytest
from pydantic import ValidationError

from src.sites.base.site_config import (
    AuthMethod,
    ExtractionMode,
    SiteConfig,
    SiteConfigLoader,
    load_site_config,
    load_site_config_or_none,
)


class TestSiteConfig:
    """Tests for SiteConfig Pydantic model."""

    def test_minimal_config(self):
        """Test minimal configuration with only required fields."""
        config = SiteConfig(endpoint="https://example.com")
        assert config.endpoint == "https://example.com"
        assert config.auth_method == AuthMethod.NONE
        # Default extraction mode is now RAW (Direct API) per story 7-1 AC #4
        assert config.extraction_mode == ExtractionMode.RAW

    def test_full_config(self):
        """Test configuration with all fields."""
        config = SiteConfig(
            endpoint="https://example.com",
            auth_method=AuthMethod.COOKIE,
            extraction_mode=ExtractionMode.INTERCEPTED,
            timeout=60,
            rate_limit=1.5,
        )
        assert config.endpoint == "https://example.com"
        assert config.auth_method == AuthMethod.COOKIE
        assert config.extraction_mode == ExtractionMode.INTERCEPTED
        assert config.timeout == 60
        assert config.rate_limit == 1.5

    def test_endpoint_validation_http(self):
        """Test that http endpoint is accepted."""
        config = SiteConfig(endpoint="http://example.com")
        assert config.endpoint == "http://example.com"

    def test_endpoint_validation_https(self):
        """Test that https endpoint is accepted."""
        config = SiteConfig(endpoint="https://example.com")
        assert config.endpoint == "https://example.com"

    def test_endpoint_validation_invalid(self):
        """Test that invalid endpoint raises error."""
        with pytest.raises(ValueError, match="must start with http"):
            SiteConfig(endpoint="example.com")

    def test_timeout_validation_min(self):
        """Test that minimum timeout is enforced."""
        config = SiteConfig(endpoint="https://example.com", timeout=1)
        assert config.timeout == 1

    def test_timeout_validation_max(self):
        """Test that maximum timeout is enforced."""
        config = SiteConfig(endpoint="https://example.com", timeout=300)
        assert config.timeout == 300

    def test_timeout_validation_out_of_range(self):
        """Test that out of range timeout raises error."""
        with pytest.raises(ValueError):
            SiteConfig(endpoint="https://example.com", timeout=0)

        with pytest.raises(ValueError):
            SiteConfig(endpoint="https://example.com", timeout=301)

    def test_auth_method_enum_values(self):
        """Test all authentication method values."""
        for method in AuthMethod:
            config = SiteConfig(
                endpoint="https://example.com",
                auth_method=method,
            )
            assert config.auth_method == method.value

    def test_extraction_mode_enum_values(self):
        """Test all extraction mode values."""
        for mode in ExtractionMode:
            config = SiteConfig(
                endpoint="https://example.com",
                extraction_mode=mode,
            )
            assert config.extraction_mode == mode.value


class TestSiteConfigLoader:
    """Tests for SiteConfigLoader class."""

    @pytest.fixture
    def temp_site_dir(self, tmp_path):
        """Create a temporary site directory with config.yaml."""
        site_dir = tmp_path / "test_site"
        site_dir.mkdir()

        config_content = """
endpoint: https://test.example.com
auth_method: bearer
extraction_mode: hybrid
timeout: 45
rate_limit: 3.0
"""
        config_file = site_dir / "config.yaml"
        config_file.write_text(config_content)

        return site_dir

    def test_load_config(self, temp_site_dir, monkeypatch):
        """Test loading configuration from file."""
        # Monkeypatch the config_path property
        def mock_config_path(self):
            return temp_site_dir / "config.yaml"

        monkeypatch.setattr(SiteConfigLoader, "config_path", property(mock_config_path))

        loader = SiteConfigLoader("test_site")
        config = loader.load()

        assert config.endpoint == "https://test.example.com"
        assert config.auth_method == "bearer"
        assert config.extraction_mode == "hybrid"
        assert config.timeout == 45
        assert config.rate_limit == 3.0

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file raises error."""
        loader = SiteConfigLoader("nonexistent_site")
        # The config_path will point to a non-existent file based on site name
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_load_or_none_returns_none_for_missing_file(self):
        """Test load_or_none returns None for missing file."""
        loader = SiteConfigLoader("nonexistent_site_xyz")
        result = loader.load_or_none()
        assert result is None

    def test_caching(self, temp_site_dir, monkeypatch):
        """Test that configuration is cached."""
        def mock_config_path(self):
            return temp_site_dir / "config.yaml"

        monkeypatch.setattr(SiteConfigLoader, "config_path", property(mock_config_path))

        loader = SiteConfigLoader("test_site")

        # Load twice
        config1 = loader.load()
        config2 = loader.load()

        # Should be the same object (cached)
        assert config1 is config2

    def test_force_reload(self, temp_site_dir, monkeypatch):
        """Test force reload bypasses cache."""
        def mock_config_path(self):
            return temp_site_dir / "config.yaml"

        monkeypatch.setattr(SiteConfigLoader, "config_path", property(mock_config_path))

        loader = SiteConfigLoader("test_site")

        config1 = loader.load()
        config2 = loader.load(force_reload=True)

        # Should be different objects after force reload
        assert config1 is not config2
        # But same values
        assert config1.endpoint == config2.endpoint

    def test_get_config_dict(self, temp_site_dir, monkeypatch):
        """Test getting configuration as dictionary."""
        def mock_config_path(self):
            return temp_site_dir / "config.yaml"

        monkeypatch.setattr(SiteConfigLoader, "config_path", property(mock_config_path))

        loader = SiteConfigLoader("test_site")
        config_dict = loader.get_config_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["endpoint"] == "https://test.example.com"
        assert config_dict["auth_method"] == "bearer"
        assert config_dict["extraction_mode"] == "hybrid"


class TestLoadSiteConfig:
    """Tests for convenience load_site_config function."""

    def test_load_from_existing_site(self):
        """Test loading config from wikipedia (existing site with config.yaml)."""
        config = load_site_config("wikipedia")

        assert config.endpoint == "https://en.wikipedia.org"
        assert config.auth_method == "none"
        assert config.extraction_mode == "intercepted"

    def test_load_flashscore_config(self):
        """Test loading config from flashscore."""
        config = load_site_config("flashscore")

        assert config.endpoint == "https://www.flashscore.com"
        assert config.auth_method == "cookie"
        assert config.extraction_mode == "intercepted"
        assert config.rate_limit == 2.0

    def test_load_nonexistent_site_raises_error(self):
        """Test loading from nonexistent site raises error."""
        with pytest.raises(FileNotFoundError):
            load_site_config("nonexistent_site_xyz")

    def test_load_site_config_or_none_nonexistent(self):
        """Test load_site_config_or_none returns None for nonexistent."""
        result = load_site_config_or_none("nonexistent_site_xyz")
        assert result is None


class TestInvalidConfig:
    """Tests for invalid configuration handling."""

    def test_empty_config_raises_error(self, tmp_path):
        """Test that empty config raises error."""
        # Create a temporary site directory with empty config
        site_dir = tmp_path / "test_site_empty"
        site_dir.mkdir()

        config_file = site_dir / "config.yaml"
        config_file.write_text("")

        # Use the Wikipedia loader but patch its config_path
        from unittest.mock import patch


        def mock_config_path(self):
            return config_file

        with patch.object(SiteConfigLoader, 'config_path', new_callable=property, fget=mock_config_path):
            loader = SiteConfigLoader("test_site_empty")
            with pytest.raises(ValueError, match="Empty configuration"):
                loader.load()

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Test that invalid YAML raises error."""
        # Create a temporary site directory with invalid YAML
        site_dir = tmp_path / "test_site_invalid"
        site_dir.mkdir()

        config_file = site_dir / "config.yaml"
        config_file.write_text("endpoint: invalid [yaml")

        # Use the Wikipedia loader but patch its config_path
        from unittest.mock import patch

        def mock_config_path(self):
            return config_file

        with patch.object(SiteConfigLoader, 'config_path', new_callable=property, fget=mock_config_path):
            loader = SiteConfigLoader("test_site_invalid")
            with pytest.raises(ValidationError):  # Pydantic validation error for invalid endpoint
                loader.load()

    def test_invalid_auth_method_raises_error(self):
        """Test that invalid auth method raises error."""
        with pytest.raises(ValueError):
            SiteConfig(
                endpoint="https://example.com",
                auth_method="invalid_method",  # type: ignore
            )
