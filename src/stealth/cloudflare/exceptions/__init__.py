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


class ChallengeTimeoutError(CloudflareConfigError):
    """Raised when challenge wait timeout is exceeded."""

    pass


class SensitivityConfigurationError(CloudflareConfigError):
    """Raised when sensitivity configuration is invalid."""

    pass


class WebdriverMaskerError(CloudflareConfigError):
    """Raised when webdriver signal suppression fails."""

    pass


class FingerprintRandomizerError(CloudflareConfigError):
    """Raised when fingerprint randomization fails."""

    pass


class UserAgentRotationError(CloudflareConfigError):
    """Raised when user agent rotation fails."""

    pass


class ViewportNormalizationError(CloudflareConfigError):
    """Raised when viewport normalization fails."""

    pass


class StealthProfileApplierError(CloudflareConfigError):
    """Raised when stealth profile application fails."""

    pass
