"""Unit tests for Cloudflare configuration module."""

import pytest
from pathlib import Path
from pydantic import ValidationError
from unittest.mock import MagicMock

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

    def test_invalid_timeout_below_5(self) -> None:
        """Test config rejects timeout below 5 seconds."""
        with pytest.raises(ValidationError):
            CloudflareConfig(challenge_timeout=4)

    def test_valid_timeout_minimum(self) -> None:
        """Test config accepts minimum valid timeout of 5 seconds."""
        config = CloudflareConfig(challenge_timeout=5)
        assert config.challenge_timeout == 5

    def test_valid_timeout_boundary_values(self) -> None:
        """Test config accepts boundary timeout values."""
        config_min = CloudflareConfig(challenge_timeout=5)
        config_max = CloudflareConfig(challenge_timeout=300)
        assert config_min.challenge_timeout == 5
        assert config_max.challenge_timeout == 300

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


class TestChallengeTimeoutError:
    """Tests for ChallengeTimeoutError exception."""

    def test_exception_message(self) -> None:
        """Test exception can be created with message."""
        from src.stealth.cloudflare.exceptions import ChallengeTimeoutError

        error = ChallengeTimeoutError("Timeout exceeded")
        assert str(error) == "Timeout exceeded"

    def test_exception_inheritance(self) -> None:
        """Test ChallengeTimeoutError inherits from CloudflareConfigError."""
        from src.stealth.cloudflare.exceptions import (
            ChallengeTimeoutError,
            CloudflareConfigError,
        )

        error = ChallengeTimeoutError("Test")
        assert isinstance(error, CloudflareConfigError)


class TestChallengeWaiter:
    """Tests for ChallengeWaiter class."""

    def test_waiter_initialization(self) -> None:
        """Test ChallengeWaiter initializes with correct values."""
        from src.stealth.cloudflare.core.waiter import ChallengeWaiter

        config = CloudflareConfig(cloudflare_protected=True, challenge_timeout=60)
        # Create a minimal mock page object
        mock_page = MagicMock()
        waiter = ChallengeWaiter(config, mock_page)
        assert waiter.get_timeout_seconds() == 60

    def test_waiter_custom_check_interval(self) -> None:
        """Test ChallengeWaiter accepts custom check interval."""
        from src.stealth.cloudflare.core.waiter import ChallengeWaiter

        config = CloudflareConfig(cloudflare_protected=True, challenge_timeout=30)
        mock_page = MagicMock()
        waiter = ChallengeWaiter(config, mock_page, check_interval=0.5)
        assert waiter.check_interval == 0.5

    def test_get_timeout_seconds(self) -> None:
        """Test get_timeout_seconds returns correct value."""
        from src.stealth.cloudflare.core.waiter import ChallengeWaiter

        config = CloudflareConfig(cloudflare_protected=True, challenge_timeout=120)
        mock_page = MagicMock()
        waiter = ChallengeWaiter(config, mock_page)
        assert waiter.get_timeout_seconds() == 120

    @pytest.mark.asyncio
    async def test_waiter_context_manager(self) -> None:
        """Test ChallengeWaiter async context manager."""
        from src.stealth.cloudflare.core.waiter import ChallengeWaiter

        config = CloudflareConfig(cloudflare_protected=True, challenge_timeout=30)
        mock_page = MagicMock()

        async with ChallengeWaiter(config, mock_page) as waiter:
            assert waiter.get_timeout_seconds() == 30

    @pytest.mark.asyncio
    async def test_wait_for_challenge_resolved_is_stub(self) -> None:
        """Test wait_for_challenge_resolved raises NotImplementedError (stub)."""
        from src.stealth.cloudflare.core.waiter import ChallengeWaiter

        config = CloudflareConfig(cloudflare_protected=True, challenge_timeout=30)
        mock_page = MagicMock()

        async def quick_check() -> bool:
            return True

        async with ChallengeWaiter(config, mock_page) as waiter:
            with pytest.raises(NotImplementedError):
                await waiter.wait_for_challenge_resolved(quick_check)

    @pytest.mark.asyncio
    async def test_wait_for_challenge_is_stub(self) -> None:
        """Test wait_for_challenge raises NotImplementedError (stub)."""
        from src.stealth.cloudflare.core.waiter import wait_for_challenge

        config = CloudflareConfig(cloudflare_protected=True, challenge_timeout=30)
        mock_page = MagicMock()

        async def quick_check() -> bool:
            return True

        with pytest.raises(NotImplementedError):
            await wait_for_challenge(config, mock_page, quick_check, timeout=60)


class TestWaitForChallenge:
    """Tests for wait_for_challenge convenience function."""

    @pytest.mark.asyncio
    async def test_wait_for_challenge_raises_not_implemented(self) -> None:
        """Test wait_for_challenge raises NotImplementedError (stub)."""
        from src.stealth.cloudflare.core.waiter import wait_for_challenge

        config = CloudflareConfig(cloudflare_protected=True, challenge_timeout=30)
        mock_page = MagicMock()

        async def quick_check() -> bool:
            return True

        with pytest.raises(NotImplementedError):
            await wait_for_challenge(config, mock_page, quick_check, timeout=60)


class TestIsWaitEnabled:
    """Tests for is_wait_enabled function."""

    def test_true_when_cloudflare_enabled(self) -> None:
        """Test returns True when Cloudflare is enabled."""
        from src.stealth.cloudflare.core.waiter import is_wait_enabled

        assert is_wait_enabled(True) is True
        assert is_wait_enabled({"cloudflare_protected": True}) is True

    def test_false_when_cloudflare_disabled(self) -> None:
        """Test returns False when Cloudflare is disabled."""
        from src.stealth.cloudflare.core.waiter import is_wait_enabled

        assert is_wait_enabled(False) is False
        assert is_wait_enabled({}) is False
        assert is_wait_enabled(None) is False
