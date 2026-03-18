"""Cloudflare configuration exceptions."""


class CloudflareConfigError(Exception):
    """Base exception for Cloudflare configuration errors."""

    pass


class CloudflareConfigValidationError(CloudflareConfigError):
    """Raised when Cloudflare configuration validation fails."""

    pass


class CloudflareConfigLoadError(CloudflareConfigError):
    """Raised when Cloudflare configuration fails to load."""

    pass


class CloudflareConfigNotFoundError(CloudflareConfigError):
    """Raised when Cloudflare configuration file is not found."""

    pass
