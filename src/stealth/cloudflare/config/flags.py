"""Flag handling logic for Cloudflare configuration."""

from typing import Any, Optional

from src.stealth.cloudflare.models.config import CloudflareConfig


def is_cloudflare_enabled(
    config: dict[str, Any] | CloudflareConfig | bool | None,
) -> bool:
    """Check if Cloudflare protection is enabled in the configuration.

    This function extracts the cloudflare_protected flag from various
    configuration formats and returns whether Cloudflare protection
    should be activated.

    Args:
        config: Configuration in one of these formats:
            - dict with cloudflare_protected key
            - CloudflareConfig instance
            - CloudflareConfigSchema instance
            - None or empty

    Returns:
        True if cloudflare_protected is set to True, False otherwise.
    """
    if config is None:
        return False

    if isinstance(config, bool):
        return config

    if isinstance(config, CloudflareConfig):
        return config.is_enabled()

    if isinstance(config, dict):
        return bool(config.get("cloudflare_protected", False))

    return False


def extract_cloudflare_config(
    config: dict[str, Any],
) -> Optional[CloudflareConfig]:
    """Extract Cloudflare configuration from a site config dictionary.

    Args:
        config: Site module configuration dictionary.

    Returns:
        CloudflareConfig instance if cloudflare_protected is True,
        None otherwise.
    """
    if not is_cloudflare_enabled(config):
        return None

    cloudflare_data = config.get("cloudflare", {})

    # Only extract if cloudflare_protected is explicitly True
    is_enabled = config.get("cloudflare_protected", False)
    if not is_enabled and not cloudflare_data.get("cloudflare_protected", False):
        return None

    return CloudflareConfig(
        cloudflare_protected=cloudflare_data.get(
            "cloudflare_protected", config.get("cloudflare_protected", False)
        ),
        challenge_timeout=cloudflare_data.get(
            "challenge_timeout", config.get("challenge_timeout", 30)
        ),
        detection_sensitivity=cloudflare_data.get(
            "detection_sensitivity", config.get("detection_sensitivity", 3)
        ),
        auto_retry=cloudflare_data.get("auto_retry", config.get("auto_retry", True)),
    )


def merge_with_defaults(
    config: Optional[dict[str, Any]],
) -> CloudflareConfig:
    """Merge provided configuration with default values.

    Args:
        config: Optional configuration dictionary.

    Returns:
        CloudflareConfig with defaults applied.
    """
    if config is None:
        return CloudflareConfig()

    return CloudflareConfig(
        cloudflare_protected=config.get("cloudflare_protected", False),
        challenge_timeout=config.get("challenge_timeout", 30),
        detection_sensitivity=config.get("detection_sensitivity", 3),
        auto_retry=config.get("auto_retry", True),
    )
