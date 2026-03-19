"""Cloudflare configuration model."""

from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.stealth.cloudflare.models.sensitivity import (
    parse_sensitivity_value,
    SensitivityConfigurationError,
)


class CloudflareConfig(BaseModel):
    """Configuration model for Cloudflare-protected sites.

    This model validates the cloudflare_protected flag and related settings
    from site module YAML configuration files.

    Attributes:
        cloudflare_protected: Whether Cloudflare protection is enabled for the site.
        challenge_timeout: Maximum time to wait for challenge completion (seconds).
        detection_sensitivity: Sensitivity level for challenge detection (1-5) or
            string value ("high", "medium", "low").
        auto_retry: Whether to automatically retry on challenge failure.
    """

    cloudflare_protected: bool = Field(
        default=False,
        description="Enable Cloudflare bypass mechanisms",
    )
    challenge_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Maximum wait time for challenge completion in seconds",
    )
    detection_sensitivity: Union[int, str] = Field(
        default=3,
        description="Challenge detection sensitivity level (1-5 or 'high', 'medium', 'low')",
    )
    auto_retry: bool = Field(
        default=True,
        description="Automatically retry on challenge failure",
    )

    model_config = ConfigDict(frozen=False, validate_assignment=True)

    @field_validator("detection_sensitivity", mode="before")
    @classmethod
    def _parse_sensitivity(cls, v: Union[int, str]) -> int:
        """Parse detection_sensitivity from string or int to int.

        Args:
            v: The sensitivity value (1-5 or "high", "medium", "low").

        Returns:
            The numeric sensitivity value (1-5).

        Raises:
            ValueError: If sensitivity value is invalid.
        """
        try:
            if isinstance(v, str) or isinstance(v, int):
                return parse_sensitivity_value(v)
            return v
        except SensitivityConfigurationError as e:
            raise ValueError(str(e)) from e

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
