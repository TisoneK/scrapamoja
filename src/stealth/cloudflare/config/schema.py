"""Pydantic validation schema for Cloudflare configuration."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class CloudflareConfigSchema(BaseModel):
    """Schema for validating Cloudflare configuration from YAML.

    This schema provides validation for the cloudflare_protected flag
    and related settings in site module configuration files.

    Attributes:
        cloudflare_protected: Whether Cloudflare protection is enabled.
        challenge_timeout: Maximum time to wait for challenge (seconds).
        detection_sensitivity: Challenge detection sensitivity (1-5).
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
    detection_sensitivity: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Detection sensitivity level",
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

    @field_validator("detection_sensitivity")
    @classmethod
    def validate_detection_sensitivity(cls, v: int) -> int:
        """Validate detection sensitivity value.

        Args:
            v: The sensitivity level (1-5).

        Returns:
            The validated sensitivity value.

        Raises:
            ValueError: If sensitivity is out of valid range.
        """
        if v < 1 or v > 5:
            msg = "detection_sensitivity must be between 1 and 5"
            raise ValueError(msg)
        return v

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
