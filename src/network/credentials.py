"""Credential sourcing from environment variables and secrets files.

This module provides functionality for reading credentials from:
1. Environment variables (primary source)
2. Gitignored secrets file (fallback source)

Security requirements (NFRs):
- NFR7: Credentials via environment variables or secrets file - not hardcoded
- NFR8: API keys in site module configs must not be committed
- NFR10: Verbose logging must warn about potential credential exposure
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any


class CredentialSource(Enum):
    """Enum representing the source of credentials."""

    ENVIRONMENT = "environment"
    SECRETS_FILE = "secrets_file"
    DEFAULT = "default"


class CredentialsManager:
    """Manages credential sourcing from environment variables and secrets files.

    Environment variable naming convention:
    - Standard prefix: SCRAPAMOJA_
    - Bearer token: SCRAPAMOJA_AUTH_TOKEN
    - Basic auth: SCRAPAMOJA_BASIC_USER, SCRAPAMOJA_BASIC_PASSWORD
    - Cookie: SCRAPAMOJA_COOKIE_JAR

    Custom site prefix (optional):
    - e.g., SCRAPAMOJA_AISCORE_AUTH_TOKEN for site-specific credentials

    Secrets file fallback:
    - Default location: .scrapamoja-secrets (gitignored)
    - YAML format with site-specific sections
    """

    # Standard environment variable names
    DEFAULT_PREFIX = "SCRAPAMOJA"
    ENV_BEARER = "AUTH_TOKEN"
    ENV_BASIC_USER = "BASIC_USER"
    ENV_BASIC_PASSWORD = "BASIC_PASSWORD"
    ENV_COOKIE = "COOKIE_JAR"

    def __init__(
        self,
        site_prefix: str | None = None,
        secrets_path: str | None = None,
    ) -> None:
        """Initialize CredentialsManager.

        Args:
            site_prefix: Optional site-specific prefix for env var names.
                        If provided, uses SCRAPAMOJA_{prefix}_ pattern.
            secrets_path: Optional path to secrets file. If not provided,
                         defaults to .scrapamoja-secrets in project root.
        """
        self._site_prefix = site_prefix
        self._secrets_path = secrets_path
        self._secrets_cache: dict[str, Any] | None = None

    def _get_env_var_name(self, base_name: str) -> str:
        """Construct full environment variable name with prefix.

        Args:
            base_name: The base name of the env var (e.g., AUTH_TOKEN).

        Returns:
            Full environment variable name (e.g., SCRAPAMOJA_AUTH_TOKEN).
        """
        if self._site_prefix:
            # Custom site prefix: SCRAPAMOJA_{PREFIX}_{BASE}
            return f"{self.DEFAULT_PREFIX}_{self._site_prefix.upper()}_{base_name}"
        return f"{self.DEFAULT_PREFIX}_{base_name}"

    def _get_secrets(self) -> dict[str, Any]:
        """Load and cache secrets from the secrets file.

        Returns:
            Dictionary of secrets, or empty dict if file doesn't exist or is invalid.
        """
        if self._secrets_cache is not None:
            return self._secrets_cache

        self._secrets_cache = {}
        secrets_path = self._secrets_path or ".scrapamoja-secrets"

        try:
            secrets_file = Path(secrets_path)
            if secrets_file.exists():
                import yaml

                content = secrets_file.read_text(encoding="utf-8")
                self._secrets_cache = yaml.safe_load(content) or {}
        except Exception:
            # If file doesn't exist or is invalid, return empty dict
            pass

        return self._secrets_cache

    def get_bearer_token(self) -> str | None:
        """Get bearer token from environment variable or secrets file.

        Returns:
            Bearer token string, or None if not found.
        """
        env_var = self._get_env_var_name(self.ENV_BEARER)
        token = os.environ.get(env_var)

        if token:
            return token

        # Fallback to secrets file
        secrets = self._get_secrets()
        site_key = self._site_prefix.lower() if self._site_prefix else "scrapamoja"
        if site_key in secrets and "auth_token" in secrets[site_key]:
            return secrets[site_key]["auth_token"]

        return None

    def get_bearer_token_with_source(self) -> tuple[str | None, CredentialSource]:
        """Get bearer token along with its source.

        Returns:
            Tuple of (token, source) where source indicates where the token came from.
        """
        env_var = self._get_env_var_name(self.ENV_BEARER)
        token = os.environ.get(env_var)

        if token:
            return token, CredentialSource.ENVIRONMENT

        # Fallback to secrets file
        secrets = self._get_secrets()
        site_key = self._site_prefix.lower() if self._site_prefix else "scrapamoja"
        if site_key in secrets and "auth_token" in secrets[site_key]:
            return secrets[site_key]["auth_token"], CredentialSource.SECRETS_FILE

        return None, CredentialSource.DEFAULT

    def get_basic_auth(self) -> tuple[str, str] | None:
        """Get basic authentication credentials from environment variables or secrets file.

        Returns:
            Tuple of (username, password), or None if not found.
        """
        user_var = self._get_env_var_name(self.ENV_BASIC_USER)
        pass_var = self._get_env_var_name(self.ENV_BASIC_PASSWORD)

        username = os.environ.get(user_var)
        password = os.environ.get(pass_var)

        if username and password:
            return (username, password)

        # Fallback to secrets file
        secrets = self._get_secrets()
        site_key = self._site_prefix.lower() if self._site_prefix else "scrapamoja"
        if site_key in secrets:
            file_user = secrets[site_key].get("basic_user")
            file_pass = secrets[site_key].get("basic_password")
            if file_user and file_pass:
                return (file_user, file_pass)

        return None

    def get_cookie(self) -> dict[str, str] | None:
        """Get cookie from environment variable or secrets file.

        Returns:
            Dictionary of cookie key-value pairs, or None if not found.
        """
        env_var = self._get_env_var_name(self.ENV_COOKIE)
        cookie_str = os.environ.get(env_var)

        if cookie_str:
            # Parse cookie string (format: "key1=value1; key2=value2")
            cookie_dict: dict[str, str] = {}
            for part in cookie_str.split(";"):
                part = part.strip()
                if "=" in part:
                    key, value = part.split("=", 1)
                    cookie_dict[key] = value
            return cookie_dict if cookie_dict else None

        # Fallback to secrets file
        secrets = self._get_secrets()
        site_key = self._site_prefix.lower() if self._site_prefix else "scrapamoja"
        if site_key in secrets and "cookie_jar" in secrets[site_key]:
            cookie_str = secrets[site_key]["cookie_jar"]
            cookie_dict: dict[str, str] = {}
            for part in cookie_str.split(";"):
                part = part.strip()
                if "=" in part:
                    key, value = part.split("=", 1)
                    cookie_dict[key] = value
            return cookie_dict if cookie_dict else None

        return None


# Flag to track if verbose warning has been shown
_verbose_warning_shown: bool = False


def check_verbose_logging_warning() -> None:
    """Log a warning if verbose mode might expose credentials.

    This should be called when verbose logging is enabled to warn
    developers about potential credential exposure in logs.

    NFR10: Opt-in verbose logging for debugging must explicitly warn
    developer that credentials may appear.
    """
    global _verbose_warning_shown

    # Check if verbose mode is enabled via environment
    verbose_enabled = os.environ.get("SCRAPAMOJA_VERBOSE", "false").lower()

    if verbose_enabled in ("true", "1", "yes") and not _verbose_warning_shown:
        try:
            import structlog

            structlog.get_logger().warning(
                "verbose_logging_security_warning",
                message=(
                    "WARNING: Verbose logging is enabled. Credentials may appear in logs. "
                    "Disable verbose logging in production. "
                    "Set SCRAPAMOJA_VERBOSE=false to disable."
                ),
            )
            _verbose_warning_shown = True
        except Exception:
            # If structlog is not available, print to stderr
            import sys

            print(
                "WARNING: Verbose logging is enabled. Credentials may appear in logs. "
                "Disable verbose logging in production. Set SCRAPAMOJA_VERBOSE=false to disable.",
                file=sys.stderr,
            )
            _verbose_warning_shown = True