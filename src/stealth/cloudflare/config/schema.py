"""Pydantic validation schema for Cloudflare configuration."""

from typing import Any, Union

from pydantic import BaseModel, Field, field_validator

from src.stealth.cloudflare.models.sensitivity import (
    SensitivityConfigurationError,
    VALID_SENSITIVITY_STRINGS,
    parse_sensitivity_value,
)


class CloudflareConfigSchema(BaseModel):
    """Schema for validating Cloudflare configuration from YAML.

    This schema provides validation for the cloudflare_protected flag
    and related settings in site module configuration files.

    Attributes:
        cloudflare_protected: Whether Cloudflare protection is enabled.
        challenge_timeout: Maximum time to wait for challenge (seconds).
        detection_sensitivity: Challenge detection sensitivity (1-5 or 'high', 'medium', 'low').
        auto_retry: Whether to automatically retry on failure.
    """

    cloudflare_protected: bool = Field(
        default=False,
        description="Enable Cloudflare bypass mechanisms",
    )
    challenge_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Maximum wait time for challenge completion",
    )
    detection_sensitivity: Union[int, str] = Field(
        default=3,
        description="Detection sensitivity level (1-5 or 'high', 'medium', 'low')",
    )
    auto_retry: bool = Field(
        default=True,
        description="Auto retry on challenge failure",
    )

    @field_validator("challenge_timeout")
    @classmethod
    def validate_challenge_timeout(cls, v: int) -> int:
        """Validate challenge timeout value.

        Args:
            v: The timeout value in seconds.

        Returns:
            The validated timeout value.

        Raises:
            ValueError: If timeout is out of valid range.
        """
        if v < 5 or v > 300:
            msg = "challenge_timeout must be between 5 and 300 seconds"
            raise ValueError(msg)
        return v

    @field_validator("detection_sensitivity", mode="before")
    @classmethod
    def validate_detection_sensitivity(cls, v: Union[int, str]) -> int:
        """Validate detection sensitivity value.

        Args:
            v: The sensitivity level (1-5 or "high", "medium", "low").

        Returns:
            The validated sensitivity value (1-5).

        Raises:
            ValueError: If sensitivity is invalid.
        """
        # If it's a string, validate it's a valid string value first
        if isinstance(v, str):
            normalized = v.lower().strip()
            if normalized not in VALID_SENSITIVITY_STRINGS:
                valid_options = list(VALID_SENSITIVITY_STRINGS) + ["1-5"]
                msg = (
                    f"detection_sensitivity must be one of: {', '.join(valid_options)}"
                )
                raise ValueError(msg)

        # Parse the value (handles both string and int)
        try:
            return parse_sensitivity_value(v)
        except SensitivityConfigurationError as e:
            raise ValueError(str(e)) from e

    def to_dict(self) -> dict[str, Any]:
        """Convert schema to dictionary.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "cloudflare_protected": self.cloudflare_protected,
            "challenge_timeout": self.challenge_timeout,
            "detection_sensitivity": self.detection_sensitivity,
            "auto_retry": self.auto_retry,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CloudflareConfigSchema":
        """Create schema from dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            CloudflareConfigSchema instance.
        """
        return cls(**data)
