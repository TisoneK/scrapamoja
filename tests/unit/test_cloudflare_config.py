"""Unit tests for Cloudflare configuration module."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from src.stealth.cloudflare.config.flags import (
    extract_cloudflare_config,
    is_cloudflare_enabled,
    merge_with_defaults,
)
from src.stealth.cloudflare.config.loader import CloudflareConfigLoader
from src.stealth.cloudflare.exceptions import (
    CloudflareConfigLoadError,
    CloudflareConfigNotFoundError,
)
from src.stealth.cloudflare.models.config import CloudflareConfig


class TestCloudflareConfig:
    """Tests for CloudflareConfig model."""

    def test_default_values(self) -> None:
        """Test that default values are applied correctly."""
        config = CloudflareConfig()
        assert config.cloudflare_protected is False
        assert config.challenge_timeout == 30
        assert config.detection_sensitivity == 3
        assert config.auto_retry is True

    def test_explicit_values(self) -> None:
        """Test that explicit values are applied correctly."""
        config = CloudflareConfig(
            cloudflare_protected=True,
            challenge_timeout=60,
            detection_sensitivity=5,
            auto_retry=False,
        )
        assert config.cloudflare_protected is True
        assert config.challenge_timeout == 60
        assert config.detection_sensitivity == 5
        assert config.auto_retry is False

    def test_is_enabled_returns_true_when_protected(self) -> None:
        """Test is_enabled returns True when cloudflare_protected is True."""
        config = CloudflareConfig(cloudflare_protected=True)
        assert config.is_enabled() is True

    def test_is_enabled_returns_false_when_not_protected(self) -> None:
        """Test is_enabled returns False when cloudflare_protected is False."""
        config = CloudflareConfig(cloudflare_protected=False)
        assert config.is_enabled() is False

    def test_to_dict(self) -> None:
        """Test to_dict method returns correct dictionary."""
        config = CloudflareConfig(
            cloudflare_protected=True,
            challenge_timeout=45,
            detection_sensitivity=4,
            auto_retry=True,
        )
        result = config.to_dict()
        assert result["cloudflare_protected"] is True
        assert result["challenge_timeout"] == 45
        assert result["detection_sensitivity"] == 4
        assert result["auto_retry"] is True


class TestCloudflareConfigValidation:
    """Tests for CloudflareConfig validation (now handles what Schema did)."""

    def test_valid_config(self) -> None:
        """Test config validates correct configuration."""
        config = CloudflareConfig(
            cloudflare_protected=True,
            challenge_timeout=30,
            detection_sensitivity=3,
            auto_retry=True,
        )
        assert config.cloudflare_protected is True
        assert config.challenge_timeout == 30
        assert config.detection_sensitivity == 3
        assert config.auto_retry is True

    def test_invalid_timeout_too_low(self) -> None:
        """Test config rejects timeout below minimum."""
        with pytest.raises(ValidationError):
            CloudflareConfig(challenge_timeout=0)

    def test_invalid_timeout_too_high(self) -> None:
        """Test config rejects timeout above maximum."""
        with pytest.raises(ValidationError):
            CloudflareConfig(challenge_timeout=301)

    def test_invalid_sensitivity_too_low(self) -> None:
        """Test config rejects sensitivity below minimum."""
        with pytest.raises(ValidationError):
            CloudflareConfig(detection_sensitivity=0)

    def test_invalid_sensitivity_too_high(self) -> None:
        """Test config rejects sensitivity above maximum."""
        with pytest.raises(ValidationError):
            CloudflareConfig(detection_sensitivity=6)

    def test_from_dict(self) -> None:
        """Test config creation from dictionary."""
        data = {
            "cloudflare_protected": True,
            "challenge_timeout": 45,
            "detection_sensitivity": 4,
            "auto_retry": False,
        }
        config = CloudflareConfig(**data)
        assert config.cloudflare_protected is True
        assert config.challenge_timeout == 45
        assert config.detection_sensitivity == 4
        assert config.auto_retry is False


class TestIsCloudflareEnabled:
    """Tests for is_cloudflare_enabled function."""

    def test_none_returns_false(self) -> None:
        """Test that None returns False."""
        assert is_cloudflare_enabled(None) is False

    def test_bool_true_returns_true(self) -> None:
        """Test that True returns True."""
        assert is_cloudflare_enabled(True) is True

    def test_bool_false_returns_false(self) -> None:
        """Test that False returns False."""
        assert is_cloudflare_enabled(False) is False

    def test_dict_with_true_flag(self) -> None:
        """Test dict with cloudflare_protected: True."""
        assert is_cloudflare_enabled({"cloudflare_protected": True}) is True

    def test_dict_with_false_flag(self) -> None:
        """Test dict with cloudflare_protected: False."""
        assert is_cloudflare_enabled({"cloudflare_protected": False}) is False

    def test_dict_without_flag(self) -> None:
        """Test dict without cloudflare_protected key."""
        assert is_cloudflare_enabled({"other": "value"}) is False

    def test_cloudflare_config_enabled(self) -> None:
        """Test CloudflareConfig with protection enabled."""
        config = CloudflareConfig(cloudflare_protected=True)
        assert is_cloudflare_enabled(config) is True

    def test_cloudflare_config_disabled(self) -> None:
        """Test CloudflareConfig with protection disabled."""
        config = CloudflareConfig(cloudflare_protected=False)
        assert is_cloudflare_enabled(config) is False


class TestExtractCloudflareConfig:
    """Tests for extract_cloudflare_config function."""

    def test_returns_none_when_not_enabled(self) -> None:
        """Test returns None when cloudflare_protected is False."""
        config = {"site_name": "example"}
        result = extract_cloudflare_config(config)
        assert result is None

    def test_returns_config_when_enabled(self) -> None:
        """Test returns CloudflareConfig when enabled."""
        config = {
            "cloudflare_protected": True,
            "challenge_timeout": 45,
            "detection_sensitivity": 4,
            "auto_retry": False,
        }
        result = extract_cloudflare_config(config)
        assert result is not None
        assert result.cloudflare_protected is True
        assert result.challenge_timeout == 45
        assert result.detection_sensitivity == 4
        assert result.auto_retry is False


class TestMergeWithDefaults:
    """Tests for merge_with_defaults function."""

    def test_none_returns_defaults(self) -> None:
        """Test None returns default configuration."""
        result = merge_with_defaults(None)
        assert result.cloudflare_protected is False
        assert result.challenge_timeout == 30
        assert result.detection_sensitivity == 3
        assert result.auto_retry is True

    def test_partial_config_merges_defaults(self) -> None:
        """Test partial config merges with defaults."""
        result = merge_with_defaults({"cloudflare_protected": True})
        assert result.cloudflare_protected is True
        assert result.challenge_timeout == 30
        assert result.detection_sensitivity == 3
        assert result.auto_retry is True


class TestCloudflareConfigLoader:
    """Tests for CloudflareConfigLoader class."""

    def test_load_from_dict(self) -> None:
        """Test loading configuration from dictionary."""
        data = {
            "cloudflare_protected": True,
            "challenge_timeout": 45,
            "detection_sensitivity": 4,
            "auto_retry": False,
        }
        loader = CloudflareConfigLoader()
        config = loader.load_from_dict(data)
        assert config.cloudflare_protected is True
        assert config.challenge_timeout == 45
        assert config.detection_sensitivity == 4
        assert config.auto_retry is False

    def test_load_from_dict_empty(self) -> None:
        """Test loading from empty dictionary returns defaults."""
        loader = CloudflareConfigLoader()
        config = loader.load_from_dict({})
        assert config.cloudflare_protected is False

    def test_load_from_site_config_enabled(self) -> None:
        """Test loading from site config with Cloudflare enabled."""
        config = {
            "site_name": "example",
            "cloudflare_protected": True,
            "challenge_timeout": 60,
        }
        result = CloudflareConfigLoader.load_from_site_config(config)
        assert result.cloudflare_protected is True
        assert result.challenge_timeout == 60

    def test_load_from_site_config_disabled(self) -> None:
        """Test loading from site config with Cloudflare disabled."""
        config = {"site_name": "example", "cloudflare_protected": False}
        result = CloudflareConfigLoader.load_from_site_config(config)
        assert result.cloudflare_protected is False

    def test_is_cloudflare_site_true(self) -> None:
        """Test is_cloudflare_site returns True for protected sites."""
        config = {"cloudflare_protected": True}
        assert CloudflareConfigLoader.is_cloudflare_site(config) is True

    def test_is_cloudflare_site_false(self) -> None:
        """Test is_cloudflare_site returns False for non-protected sites."""
        config = {"cloudflare_protected": False}
        assert CloudflareConfigLoader.is_cloudflare_site(config) is False

    def test_is_cloudflare_site_nested(self) -> None:
        """Test is_cloudflare_site detects nested config."""
        config = {"cloudflare": {"cloudflare_protected": True}}
        assert CloudflareConfigLoader.is_cloudflare_site(config) is True

    def test_load_valid_file(self, tmp_path) -> None:
        """Test loading configuration from a YAML file."""
        config_file = tmp_path / "cloudflare.yaml"
        config_file.write_text("""
cloudflare_protected: true
challenge_timeout: 45
detection_sensitivity: 4
auto_retry: false
""")
        loader = CloudflareConfigLoader(config_file)
        config = loader.load()
        assert config.cloudflare_protected is True
        assert config.challenge_timeout == 45
        assert config.detection_sensitivity == 4
        assert config.auto_retry is False

    def test_load_file_not_found(self, tmp_path) -> None:
        """Test load raises error when file doesn't exist."""
        loader = CloudflareConfigLoader(Path("/nonexistent/path.yaml"))
        with pytest.raises(CloudflareConfigNotFoundError):
            loader.load()

    def test_load_empty_file(self, tmp_path) -> None:
        """Test loading empty YAML file returns defaults."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        loader = CloudflareConfigLoader(config_file)
        config = loader.load()
        assert config.cloudflare_protected is False
        assert config.challenge_timeout == 30

    def test_load_invalid_yaml(self, tmp_path) -> None:
        """Test load raises error for invalid YAML."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:")
        loader = CloudflareConfigLoader(config_file)
        with pytest.raises(CloudflareConfigLoadError):
            loader.load()
