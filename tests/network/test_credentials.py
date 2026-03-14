"""Unit tests for credential sourcing from environment variables and secrets files."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.network.credentials import CredentialSource, CredentialsManager


@pytest.mark.unit
class TestCredentialSource:
    """Tests for CredentialSource enum."""

    def test_environment_source_is_correct(self) -> None:
        """Test that CredentialSource.ENVIRONMENT has correct value."""
        assert CredentialSource.ENVIRONMENT.value == "environment"

    def test_secrets_file_source_is_correct(self) -> None:
        """Test that CredentialSource.SECRETS_FILE has correct value."""
        assert CredentialSource.SECRETS_FILE.value == "secrets_file"

    def test_default_source_is_correct(self) -> None:
        """Test that CredentialSource.DEFAULT has correct value."""
        assert CredentialSource.DEFAULT.value == "default"


@pytest.mark.unit
class TestCredentialsManager:
    """Tests for CredentialsManager class."""

    def test_init_with_default_values(self) -> None:
        """Test that CredentialsManager initializes with default values."""
        manager = CredentialsManager()
        assert manager._site_prefix is None

    def test_init_with_custom_prefix(self) -> None:
        """Test that CredentialsManager accepts custom site prefix."""
        manager = CredentialsManager(site_prefix="aiscore")
        assert manager._site_prefix == "aiscore"

    @patch.dict(os.environ, {"SCRAPAMOJA_AUTH_TOKEN": "test-token-123"}, clear=False)
    def test_get_bearer_token_from_env(self) -> None:
        """Test that bearer token is read from SCRAPAMOJA_AUTH_TOKEN."""
        manager = CredentialsManager()
        token = manager.get_bearer_token()
        assert token == "test-token-123"

    @patch.dict(os.environ, {"SCRAPAMOJA_BASIC_USER": "testuser", "SCRAPAMOJA_BASIC_PASSWORD": "testpass"}, clear=False)
    def test_get_basic_auth_from_env(self) -> None:
        """Test that basic auth is read from SCRAPAMOJA_BASIC_USER and SCRAPAMOJA_BASIC_PASSWORD."""
        manager = CredentialsManager()
        credentials = manager.get_basic_auth()
        assert credentials == ("testuser", "testpass")

    @patch.dict(os.environ, {"SCRAPAMOJA_COOKIE_JAR": "session=abc123;user=john"}, clear=False)
    def test_get_cookie_from_env(self) -> None:
        """Test that cookie is read from SCRAPAMOJA_COOKIE_JAR."""
        manager = CredentialsManager()
        cookie = manager.get_cookie()
        assert cookie == {"session": "abc123", "user": "john"}

    @patch.dict(os.environ, {"SCRAPAMOJA_AISCORE_AUTH_TOKEN": "site-token"}, clear=False)
    def test_get_bearer_token_with_custom_prefix(self) -> None:
        """Test that custom site prefix is used for env var lookup."""
        manager = CredentialsManager(site_prefix="aiscore")
        token = manager.get_bearer_token()
        assert token == "site-token"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_bearer_token_returns_none_when_not_set(self) -> None:
        """Test that None is returned when env var is not set."""
        manager = CredentialsManager()
        token = manager.get_bearer_token()
        assert token is None

    @patch.dict(os.environ, {}, clear=True)
    def test_get_basic_auth_returns_none_when_not_set(self) -> None:
        """Test that None is returned when basic auth env vars are not set."""
        manager = CredentialsManager()
        credentials = manager.get_basic_auth()
        assert credentials is None

    @patch.dict(os.environ, {"SCRAPAMOJA_BASIC_USER": "user"}, clear=False)
    def test_get_basic_auth_returns_none_when_password_missing(self) -> None:
        """Test that None is returned when only username is set."""
        manager = CredentialsManager()
        credentials = manager.get_basic_auth()
        assert credentials is None

    @patch.dict(os.environ, {}, clear=True)
    def test_get_cookie_returns_none_when_not_set(self) -> None:
        """Test that None is returned when cookie env var is not set."""
        manager = CredentialsManager()
        cookie = manager.get_cookie()
        assert cookie is None


@pytest.mark.unit
class TestCredentialsManagerWithSecretsFile:
    """Tests for CredentialsManager secrets file fallback."""

    @patch.dict(os.environ, {}, clear=True)
    def test_get_bearer_token_from_secrets_file(self) -> None:
        """Test that bearer token is read from secrets file when env var not set."""
        # Mock the Path to return the secrets content
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "---\nscrapamoja:\n  auth_token: file-token\n  basic_user: fileuser\n  basic_password: filepass\n"

        with patch("src.network.credentials.Path", return_value=mock_path):
            manager = CredentialsManager(secrets_path=".scrapamoja-secrets")
            token = manager.get_bearer_token()
            assert token == "file-token"

    @patch.dict(os.environ, {}, clear=True)
    def test_env_takes_precedence_over_secrets_file(self) -> None:
        """Test that environment variables take precedence over secrets file."""
        with patch.dict(os.environ, {"SCRAPAMOJA_AUTH_TOKEN": "env-token"}):
            manager = CredentialsManager(secrets_path=".scrapamoja-secrets")
            token = manager.get_bearer_token()
            assert token == "env-token"


@pytest.mark.unit
class TestCredentialSourceTracking:
    """Tests for tracking which source credentials came from."""

    @patch.dict(os.environ, {"SCRAPAMOJA_AUTH_TOKEN": "test-token"}, clear=False)
    def test_track_source_for_bearer(self) -> None:
        """Test that source is tracked when getting bearer token."""
        manager = CredentialsManager()
        token, source = manager.get_bearer_token_with_source()
        assert token == "test-token"
        assert source == CredentialSource.ENVIRONMENT