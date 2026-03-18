"""Cloudflare configuration model."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CloudflareConfig(BaseModel):
    """Configuration model for Cloudflare-protected sites.

    This model validates the cloudflare_protected flag and related settings
    from site module YAML configuration files.

    Attributes:
        cloudflare_protected: Whether Cloudflare protection is enabled for the site.
        challenge_timeout: Maximum time to wait for challenge completion (seconds).
        detection_sensitivity: Sensitivity level for challenge detection (1-5).
        auto_retry: Whether to automatically retry on challenge failure.
    """

    cloudflare_protected: bool = Field(
        default=False,
        description="Enable Cloudflare bypass mechanisms",
    )
    challenge_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Maximum wait time for challenge completion in seconds",
    )
    detection_sensitivity: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Challenge detection sensitivity level (1=low, 5=high)",
    )
    auto_retry: bool = Field(
        default=True,
        description="Automatically retry on challenge failure",
    )

    model_config = ConfigDict(frozen=False, validate_assignment=True)

    def is_enabled(self) -> bool:
        """Check if Cloudflare protection is enabled.

        Returns:
            True if cloudflare_protected is set to True.
        """
        return self.cloudflare_protected

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "cloudflare_protected": self.cloudflare_protected,
            "challenge_timeout": self.challenge_timeout,
            "detection_sensitivity": self.detection_sensitivity,
            "auto_retry": self.auto_retry,
        }
