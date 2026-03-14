"""Unit tests for session harvesting module.

Tests for SCR-006 (Session Harvesting) and SCR-007 (Session Bootstrap Mode).
"""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.network.session import (
    SessionCookies,
    SessionHeaders,
    SessionPackage,
    SessionHarvester,
    SessionValidator,
    create_session_harvester,
    create_session_validator,
)


class TestSessionCookies:
    """Tests for SessionCookies dataclass."""

    def test_session_cookies_creation(self):
        """Test creating a SessionCookies instance."""
        cookie = SessionCookies(
            name="session_id",
            value="abc123",
            domain=".example.com",
            path="/",
            expires=1234567890.0,
            http_only=True,
            secure=True,
            same_site="Lax",
        )

        assert cookie.name == "session_id"
        assert cookie.value == "abc123"
        assert cookie.domain == ".example.com"
        assert cookie.path == "/"
        assert cookie.expires == 1234567890.0
        assert cookie.http_only is True
        assert cookie.secure is True
        assert cookie.same_site == "Lax"

    def test_session_cookies_to_dict_redacts_value(self):
        """Test that to_dict redacts the value for security (NFR5, NFR6, NFR9)."""
        cookie = SessionCookies(
            name="session_id",
            value="secret_token",
            domain=".example.com",
        )

        result = cookie.to_dict()

        assert result["name"] == "session_id"
        assert result["value"] == "[REDACTED]"
        assert result["domain"] == ".example.com"


class TestSessionHeaders:
    """Tests for SessionHeaders dataclass."""

    def test_session_headers_creation(self):
        """Test creating a SessionHeaders instance."""
        header = SessionHeaders(
            name="Authorization",
            value="Bearer token123",
        )

        assert header.name == "Authorization"
        assert header.value == "Bearer token123"  # Stores full value

    def test_session_headers_to_dict_redacts_value(self):
        """Test that to_dict redacts the value for security."""
        header = SessionHeaders(
            name="Authorization",
            value="Bearer secret_token",
        )

        result = header.to_dict()

        assert result["name"] == "Authorization"
        assert result["value"] == "[REDACTED]"

    def test_is_auth_header(self):
        """Test is_auth_header property."""
        auth_header = SessionHeaders(name="Authorization", value="Bearer token")
        csrf_header = SessionHeaders(name="X-CSRF-Token", value="token")
        cookie_header = SessionHeaders(name="Cookie", value="session=abc")
        regular_header = SessionHeaders(name="Content-Type", value="application/json")

        assert auth_header.is_auth_header is True
        assert csrf_header.is_auth_header is True
        assert cookie_header.is_auth_header is True
        assert regular_header.is_auth_header is False


class TestSessionPackage:
    """Tests for SessionPackage dataclass."""

    def test_session_package_creation(self):
        """Test creating a SessionPackage instance."""
        cookies = [
            SessionCookies(name="session", value="abc", domain=".example.com"),
        ]
        headers = [
            SessionHeaders(name="Authorization", value="Bearer token"),
        ]

        package = SessionPackage(
            site_name="test_site",
            cookies=cookies,
            headers=headers,
            local_storage={"key": "value"},
            session_storage={"session_key": "session_value"},
            user_agent="Mozilla/5.0",
            viewport={"width": 1920, "height": 1080},
        )

        assert package.site_name == "test_site"
        assert len(package.cookies) == 1
        assert len(package.headers) == 1
        assert package.local_storage == {"key": "value"}
        assert package.session_storage == {"session_key": "session_value"}
        assert package.user_agent == "Mozilla/5.0"
        assert package.viewport == {"width": 1920, "height": 1080}

    def test_session_package_to_cookie_header(self):
        """Test generating Cookie header from cookies."""
        cookies = [
            SessionCookies(name="session", value="abc", domain=".example.com"),
            SessionCookies(name="user", value="john", domain=".example.com"),
        ]

        package = SessionPackage(site_name="test", cookies=cookies)

        header = package.to_cookie_header()

        assert "session=abc" in header
        assert "user=john" in header
        assert "; " in header  # Should be semicolon-separated

    def test_session_package_to_cookie_header_expires(self):
        """Test that expired cookies are excluded."""
        # Create an expired cookie
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
        cookies = [
            SessionCookies(
                name="expired",
                value="abc",
                domain=".example.com",
                expires=past_time,
            ),
            SessionCookies(
                name="valid",
                value="xyz",
                domain=".example.com",
                expires=None,  # Session cookie
            ),
        ]

        package = SessionPackage(site_name="test", cookies=cookies)

        header = package.to_cookie_header()

        assert "valid=xyz" in header
        assert "expired=" not in header

    def test_get_auth_header(self):
        """Test getting specific auth header."""
        headers = [
            SessionHeaders(name="Authorization", value="Bearer token123"),
            SessionHeaders(name="X-Custom", value="value"),
        ]

        package = SessionPackage(site_name="test", headers=headers)

        auth_header = package.get_auth_header("Authorization")
        assert auth_header == "Bearer token123"  # Returns full value

        custom_header = package.get_auth_header("X-Custom")
        assert custom_header == "value"

        missing_header = package.get_auth_header("Missing")
        assert missing_header is None

    def test_get_bearer_token(self):
        """Test extracting Bearer token."""
        headers = [
            SessionHeaders(name="Authorization", value="Bearer my_token"),
        ]

        package = SessionPackage(site_name="test", headers=headers)

        token = package.get_bearer_token()
        assert token == "my_token"

    def test_get_bearer_token_no_bearer(self):
        """Test extracting Bearer token when not present."""
        headers = [
            SessionHeaders(name="Authorization", value="Basic abc123"),
        ]

        package = SessionPackage(site_name="test", headers=headers)

        token = package.get_bearer_token()
        assert token is None

    def test_has_credentials(self):
        """Test has_credentials property."""
        # No credentials
        package1 = SessionPackage(site_name="test")
        assert package1.has_credentials is False

        # With cookies
        cookies = [SessionCookies(name="s", value="v", domain=".example.com")]
        package2 = SessionPackage(site_name="test", cookies=cookies)
        assert package2.has_credentials is True

        # With bearer token
        headers = [SessionHeaders(name="Authorization", value="Bearer token")]
        package3 = SessionPackage(site_name="test", headers=headers)
        assert package3.has_credentials is True

    def test_to_dict_redacts_credentials(self):
        """Test that to_dict redacts sensitive data."""
        cookies = [
            SessionCookies(name="session", value="secret", domain=".example.com"),
        ]
        headers = [
            SessionHeaders(name="Authorization", value="Bearer token"),
        ]

        package = SessionPackage(
            site_name="test",
            cookies=cookies,
            headers=headers,
            local_storage={"key": "value"},
        )

        result = package.to_dict()

        # Check cookies are redacted
        assert result["cookies"][0]["value"] == "[REDACTED]"
        # Check headers are redacted
        assert result["headers"][0]["value"] == "[REDACTED]"
        # Check local storage keys are present but not values
        assert "key" in result["local_storage_keys"]

    def test_save_and_load_json(self):
        """Test saving and loading session package as JSON."""
        cookies = [
            SessionCookies(
                name="session",
                value="abc123",
                domain=".example.com",
                path="/",
                expires=1234567890.0,
                http_only=True,
                secure=True,
                same_site="Lax",
            ),
        ]
        headers = [
            SessionHeaders(name="Authorization", value="Bearer token"),
        ]

        original = SessionPackage(
            site_name="test_site",
            cookies=cookies,
            headers=headers,
            local_storage={"key": "value"},
            session_storage={"session_key": "session_value"},
            user_agent="Mozilla/5.0",
            viewport={"width": 1920, "height": 1080},
        )

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            original.save_to_file(temp_path)

            # Load back
            loaded = SessionPackage.load_from_file(temp_path)

            assert loaded.site_name == original.site_name
            assert len(loaded.cookies) == len(original.cookies)
            assert loaded.cookies[0].name == original.cookies[0].name
            assert loaded.cookies[0].value == original.cookies[0].value  # Values preserved in file
            assert len(loaded.headers) == len(original.headers)
            assert loaded.local_storage == original.local_storage
            assert loaded.user_agent == original.user_agent
        finally:
            temp_path.unlink()

    def test_save_and_load_yaml(self):
        """Test saving and loading session package as YAML."""
        original = SessionPackage(
            site_name="test_site",
            cookies=[
                SessionCookies(name="session", value="abc", domain=".example.com")
            ],
        )

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = Path(f.name)

        try:
            original.save_to_file(temp_path)

            # Load back
            loaded = SessionPackage.load_from_file(temp_path)

            assert loaded.site_name == original.site_name
            assert len(loaded.cookies) == 1
        finally:
            temp_path.unlink()


class TestSessionValidator:
    """Tests for SessionValidator class."""

    def test_is_expired_no_ttl(self):
        """Test that session with no TTL is not expired."""
        validator = SessionValidator(session_ttl=None)

        session = SessionPackage(site_name="test")

        assert validator.is_expired(session) is False

    def test_is_expired_with_ttl(self):
        """Test that session is expired after TTL."""
        validator = SessionValidator(session_ttl=3600)  # 1 hour

        # Fresh session
        fresh_session = SessionPackage(site_name="test")
        assert validator.is_expired(fresh_session) is False

        # Old session (simulate by modifying harvested_at)
        old_session = SessionPackage(site_name="test")
        old_session.harvested_at = datetime.now(timezone.utc) - timedelta(hours=2)
        assert validator.is_expired(old_session) is True

    def test_is_auth_error(self):
        """Test auth error detection."""
        validator = SessionValidator()

        assert validator.is_auth_error(401) is True
        assert validator.is_auth_error(403) is True
        assert validator.is_auth_error(419) is True  # Laravel CSRF
        assert validator.is_auth_error(440) is True  # Windows logon

        assert validator.is_auth_error(200) is False
        assert validator.is_auth_error(404) is False
        assert validator.is_auth_error(500) is False

    def test_record_auth_failure(self):
        """Test auth failure tracking."""
        validator = SessionValidator(max_auth_failures=3)

        # First failures should not trigger max
        assert validator.record_auth_failure() is False
        assert validator.record_auth_failure() is False
        assert validator.auth_failure_count == 2

        # Third failure triggers max
        assert validator.record_auth_failure() is True
        assert validator.auth_failure_count == 3

    def test_reset_auth_failures(self):
        """Test resetting auth failure count."""
        validator = SessionValidator(max_auth_failures=2)

        validator.record_auth_failure()
        validator.record_auth_failure()

        assert validator.auth_failure_count == 2

        validator.reset_auth_failures()

        assert validator.auth_failure_count == 0


class TestSessionHarvester:
    """Tests for SessionHarvester class."""

    @pytest.mark.asyncio
    async def test_harvest_cookies(self):
        """Test harvesting cookies from page."""
        harvester = SessionHarvester()

        # Mock page with cookies
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.cookies = AsyncMock(
            return_value=[
                {
                    "name": "session",
                    "value": "abc123",
                    "domain": ".example.com",
                    "path": "/",
                    "expires": None,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                }
            ]
        )
        mock_page.context = mock_context
        mock_page.evaluate = AsyncMock(return_value={})
        mock_page.viewport_size = {"width": 1920, "height": 1080}

        session = await harvester.harvest(mock_page, site_name="test")

        assert len(session.cookies) == 1
        assert session.cookies[0].name == "session"
        assert session.site_name == "test"

    @pytest.mark.asyncio
    async def test_harvest_local_storage(self):
        """Test harvesting local storage."""
        harvester = SessionHarvester()

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.cookies = AsyncMock(return_value=[])
        mock_page.context = mock_context
        mock_page.evaluate = AsyncMock(
            return_value={"auth_token": "secret_token", "user_id": "123"}
        )
        mock_page.viewport_size = None

        session = await harvester.harvest(mock_page, site_name="test")

        assert session.local_storage["auth_token"] == "secret_token"
        assert session.local_storage["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_harvest_user_agent(self):
        """Test harvesting user agent."""
        harvester = SessionHarvester()

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.cookies = AsyncMock(return_value=[])
        mock_page.context = mock_context
        # Order: local_storage, session_storage, user_agent
        mock_page.evaluate = AsyncMock(
            side_effect=[
                {},  # localStorage
                {},  # sessionStorage
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",  # userAgent
            ]
        )
        mock_page.viewport_size = None

        session = await harvester.harvest(mock_page, site_name="test")

        assert session.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


class TestCreateFunctions:
    """Tests for convenience create functions."""

    def test_create_session_harvester(self):
        """Test create_session_harvester function."""
        harvester = create_session_harvester()
        assert isinstance(harvester, SessionHarvester)

    def test_create_session_validator_default(self):
        """Test create_session_validator with defaults."""
        validator = create_session_validator()
        assert isinstance(validator, SessionValidator)
        assert validator.session_ttl is None
        assert validator.max_auth_failures == 3

    def test_create_session_validator_with_ttl(self):
        """Test create_session_validator with custom TTL."""
        validator = create_session_validator(session_ttl=3600)
        assert isinstance(validator, SessionValidator)
        assert validator.session_ttl == 3600
