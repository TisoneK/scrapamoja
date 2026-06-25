"""Session harvesting module for hybrid mode extraction.

This module implements SCR-006 (Session Harvesting) - extracting cookies, tokens,
and headers from a Playwright browser context to enable direct HTTP requests.

Following Pattern 1: Protocol-Based Interface - uses dataclasses and duck typing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SessionCookies:
    """Container for harvested cookie data.

    Attributes:
        name: Cookie name
        value: Cookie value (should be redacted in logs - NFR5, NFR6, NFR9)
        domain: Cookie domain
        path: Cookie path
        expires: Expiration timestamp (Unix epoch seconds)
        http_only: Whether cookie is HTTP-only
        secure: Whether cookie is secure
        same_site: SameSite attribute value
    """

    name: str
    value: str
    domain: str
    path: str = "/"
    expires: float | None = None
    http_only: bool = False
    secure: bool = False
    same_site: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, redacting sensitive values."""
        return {
            "name": self.name,
            "value": "[REDACTED]",  # NFR5, NFR6, NFR9 - never log raw values
            "domain": self.domain,
            "path": self.path,
            "expires": self.expires,
            "http_only": self.http_only,
            "secure": self.secure,
            "same_site": self.same_site,
        }


@dataclass
class SessionHeaders:
    """Container for harvested authentication headers.

    Attributes:
        name: Header name (e.g., 'Authorization', 'X-CSRF-Token')
        value: Header value (should be redacted in logs - NFR5, NFR6, NFR9)
    """

    name: str
    value: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, redacting sensitive values."""
        return {
            "name": self.name,
            "value": "[REDACTED]",  # NFR5, NFR6, NFR9 - never log raw values
        }

    @property
    def is_auth_header(self) -> bool:
        """Check if this is an authentication-related header."""
        auth_headers = {
            "authorization",
            "x-csrf-token",
            "x-xsrf-token",
            "x-auth-token",
            "cookie",
        }
        return self.name.lower() in auth_headers


@dataclass
class SessionPackage:
    """Portable session data package for hybrid mode extraction.

    This dataclass holds all the credentials harvested from a browser session
    that can be used to make authenticated direct HTTP requests.

    Attributes:
        site_name: Name of the site this session is for
        harvested_at: Timestamp when session was harvested (UTC)
        cookies: List of harvested cookies
        headers: List of harvested headers
        local_storage: Local storage data (optional)
        session_storage: Session storage data (optional)
        user_agent: User agent string from browser
        viewport: Viewport configuration
    """

    site_name: str
    harvested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    cookies: list[SessionCookies] = field(default_factory=list)
    headers: list[SessionHeaders] = field(default_factory=list)
    local_storage: dict[str, str] = field(default_factory=dict)
    session_storage: dict[str, str] = field(default_factory=dict)
    user_agent: str | None = None
    viewport: dict[str, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with redacted credentials for logging."""
        return {
            "site_name": self.site_name,
            "harvested_at": self.harvested_at.isoformat(),
            "cookies": [c.to_dict() for c in self.cookies],
            "headers": [h.to_dict() for h in self.headers],
            "local_storage_keys": list(self.local_storage.keys()),  # Only keys, not values
            "session_storage_keys": list(self.session_storage.keys()),
            "user_agent": self.user_agent,
            "viewport": self.viewport,
        }

    def to_cookie_header(self) -> str:
        """Generate Cookie header value from harvested cookies.

        Returns:
            Formatted cookie header string (e.g., "name1=value1; name2=value2")
        """
        cookie_parts = []
        for cookie in self.cookies:
            # Skip cookies that have expired
            if cookie.expires is not None:
                # Check if expired (compare with current time)
                now = datetime.now(UTC).timestamp()
                if cookie.expires < now:
                    continue
            cookie_parts.append(f"{cookie.name}={cookie.value}")
        return "; ".join(cookie_parts)

    def get_auth_header(self, name: str = "Authorization") -> str | None:
        """Get a specific authentication header value.

        Args:
            name: Header name to look for

        Returns:
            Header value if found, None otherwise
        """
        for header in self.headers:
            if header.name.lower() == name.lower():
                return header.value
        return None

    def get_bearer_token(self) -> str | None:
        """Get Bearer token if present in headers.

        Returns:
            Bearer token value if found, None otherwise
        """
        auth = self.get_auth_header("Authorization")
        if auth and auth.startswith("Bearer "):
            return auth[7:]  # Remove "Bearer " prefix
        return None

    @property
    def has_credentials(self) -> bool:
        """Check if this session package has any credentials.

        Returns:
            True if cookies or auth headers are present
        """
        return bool(self.cookies or self.get_bearer_token())

    def save_to_file(self, path: Path) -> None:
        """Save session package to file.

        Args:
            path: File path to save to (JSON or YAML)
        """
        data = {
            "site_name": self.site_name,
            "harvested_at": self.harvested_at.isoformat(),
            "cookies": [
                {
                    "name": c.name,
                    "value": c.value,  # Raw value for persistence
                    "domain": c.domain,
                    "path": c.path,
                    "expires": c.expires,
                    "http_only": c.http_only,
                    "secure": c.secure,
                    "same_site": c.same_site,
                }
                for c in self.cookies
            ],
            "headers": [
                {"name": h.name, "value": h.value}
                for h in self.headers
            ],
            "local_storage": self.local_storage,
            "session_storage": self.session_storage,
            "user_agent": self.user_agent,
            "viewport": self.viewport,
        }

        # Determine format from extension
        if path.suffix in (".yaml", ".yml"):
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    @classmethod
    def load_from_file(cls, path: Path) -> SessionPackage:
        """Load session package from file.

        Args:
            path: File path to load from

        Returns:
            Loaded SessionPackage instance
        """
        with open(path, encoding="utf-8") as f:
            if path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        cookies = [
            SessionCookies(
                name=c["name"],
                value=c["value"],
                domain=c["domain"],
                path=c.get("path", "/"),
                expires=c.get("expires"),
                http_only=c.get("http_only", False),
                secure=c.get("secure", False),
                same_site=c.get("same_site"),
            )
            for c in data.get("cookies", [])
        ]

        headers = [
            SessionHeaders(name=h["name"], value=h["value"])
            for h in data.get("headers", [])
        ]

        return cls(
            site_name=data["site_name"],
            harvested_at=datetime.fromisoformat(data["harvested_at"]),
            cookies=cookies,
            headers=headers,
            local_storage=data.get("local_storage", {}),
            session_storage=data.get("session_storage", {}),
            user_agent=data.get("user_agent"),
            viewport=data.get("viewport"),
        )


class SessionHarvester:
    """Harvests session data from Playwright browser context.

    This class extracts cookies, tokens, headers, and storage data from
    an active Playwright browser context for use in direct HTTP requests.

    Example:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto("https://example.com")

            harvester = SessionHarvester()
            session = await harvester.harvest(page, site_name="example")

            # Now use session for direct HTTP requests
            await browser.close()
    """

    def __init__(self) -> None:
        """Initialize the session harvester."""
        pass

    async def harvest(
        self,
        page: Any,
        site_name: str,
    ) -> SessionPackage:
        """Harvest session data from a Playwright page.

        Args:
            page: Playwright async page object
            site_name: Name of the site being harvested

        Returns:
            SessionPackage containing harvested credentials
        """
        # Harvest cookies
        cookies = await self._harvest_cookies(page)

        # Harvest local storage
        local_storage = await self._harvest_local_storage(page)

        # Harvest session storage
        session_storage = await self._harvest_session_storage(page)

        # Get user agent
        user_agent = await self._get_user_agent(page)

        # Get viewport
        viewport = await self._get_viewport(page)

        return SessionPackage(
            site_name=site_name,
            cookies=cookies,
            headers=[],  # Headers come from response headers, not page
            local_storage=local_storage,
            session_storage=session_storage,
            user_agent=user_agent,
            viewport=viewport,
        )

    async def _harvest_cookies(self, page: Any) -> list[SessionCookies]:
        """Harvest cookies from the page context.

        Args:
            page: Playwright async page object

        Returns:
            List of SessionCookies
        """
        try:
            # Get all cookies from the context
            cookies = await page.context.cookies()
            return [
                SessionCookies(
                    name=c["name"],
                    value=c["value"],
                    domain=c["domain"],
                    path=c.get("path", "/"),
                    expires=c.get("expires"),
                    http_only=c.get("httpOnly", False),
                    secure=c.get("secure", False),
                    same_site=c.get("sameSite"),
                )
                for c in cookies
            ]
        except Exception:
            return []

    async def _harvest_local_storage(self, page: Any) -> dict[str, str]:
        """Harvest local storage data.

        Args:
            page: Playwright async page object

        Returns:
            Dictionary of local storage key-value pairs
        """
        try:
            result = await page.evaluate("""() => {
                const items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }""")
            return result or {}
        except Exception:
            return {}

    async def _harvest_session_storage(self, page: Any) -> dict[str, str]:
        """Harvest session storage data.

        Args:
            page: Playwright async page object

        Returns:
            Dictionary of session storage key-value pairs
        """
        try:
            result = await page.evaluate("""() => {
                const items = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    items[key] = sessionStorage.getItem(key);
                }
                return items;
            }""")
            return result or {}
        except Exception:
            return {}

    async def _get_user_agent(self, page: Any) -> str | None:
        """Get the user agent from the page.

        Args:
            page: Playwright async page object

        Returns:
            User agent string
        """
        try:
            return await page.evaluate("navigator.userAgent")
        except Exception:
            return None

    async def _get_viewport(self, page: Any) -> dict[str, int] | None:
        """Get the viewport configuration.

        Args:
            page: Playwright async page object

        Returns:
            Viewport dimensions
        """
        try:
            viewport = page.viewport_size
            if viewport:
                return {"width": viewport["width"], "height": viewport["height"]}
        except Exception:
            pass
        return None


class SessionValidator:
    """Validates session package for freshness and validity.

    This class checks if a harvested session is still valid and
    detects when re-bootstrap is needed.
    """

    # HTTP status codes that indicate auth/session expiration
    AUTH_ERROR_CODES = {401, 403, 419, 440}  # 419 = Laravel CSRF, 440 = Windows logon

    def __init__(
        self,
        session_ttl: int | None = None,
        max_auth_failures: int = 3,
    ) -> None:
        """Initialize the session validator.

        Args:
            session_ttl: Optional session time-to-live in seconds
            max_auth_failures: Maximum auth failures before re-bootstrap
        """
        self.session_ttl = session_ttl
        self.max_auth_failures = max_auth_failures
        self._auth_failure_count = 0

    def is_expired(self, session: SessionPackage) -> bool:
        """Check if session has expired based on TTL.

        Args:
            session: Session package to check

        Returns:
            True if session has expired
        """
        if self.session_ttl is None:
            return False

        now = datetime.now(UTC)
        age = (now - session.harvested_at).total_seconds()
        return age > self.session_ttl

    def is_auth_error(self, status_code: int) -> bool:
        """Check if status code indicates authentication error.

        Args:
            status_code: HTTP status code

        Returns:
            True if this is an auth-related error
        """
        return status_code in self.AUTH_ERROR_CODES

    def record_auth_failure(self) -> bool:
        """Record an authentication failure.

        Returns:
            True if max failures reached (re-bootstrap needed)
        """
        self._auth_failure_count += 1
        return self._auth_failure_count >= self.max_auth_failures

    def reset_auth_failures(self) -> None:
        """Reset the auth failure counter."""
        self._auth_failure_count = 0

    @property
    def auth_failure_count(self) -> int:
        """Get current auth failure count."""
        return self._auth_failure_count


# Convenience function for creating configured harvester
def create_session_harvester() -> SessionHarvester:
    """Create a configured SessionHarvester instance.

    Returns:
        Configured SessionHarvester
    """
    return SessionHarvester()


def create_session_validator(session_ttl: int | None = None) -> SessionValidator:
    """Create a configured SessionValidator instance.

    Args:
        session_ttl: Optional session time-to-live in seconds

    Returns:
        Configured SessionValidator
    """
    return SessionValidator(session_ttl=session_ttl)
