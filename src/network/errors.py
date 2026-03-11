"""Shared error model for network module.

This is the single deliberate cross-boundary import in the entire codebase.
Error structure: {module, operation, url, status_code, detail, partial_data}
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel

__all__ = ["NetworkError", "Retryable"]


class Retryable(str, Enum):
    """Enum for retryable vs terminal errors."""

    RETRYABLE = "retryable"
    TERMINAL = "terminal"


class NetworkError(BaseModel):
    """Structured error for network operations.

    Attributes:
        module: The module that raised the error (e.g., 'direct_api')
        operation: The operation that failed (e.g., 'get', 'post')
        url: The URL that was being accessed
        status_code: HTTP status code if applicable
        detail: Human-readable error detail
        partial_data: Any partial data that was retrieved before failure
        retryable: Whether the error is retryable
    """

    model_config = {"use_enum_values": True}

    module: str
    operation: str
    url: str | None = None
    status_code: int | None = None
    detail: str | None = None
    partial_data: Any = None
    retryable: Retryable = Retryable.TERMINAL

    def __str__(self) -> str:
        parts = [f"{self.module}.{self.operation}"]
        if self.url:
            parts.append(f"url={self.url}")
        if self.status_code:
            parts.append(f"status={self.status_code}")
        if self.detail:
            parts.append(f"detail={self.detail}")
        return "NetworkError(" + ", ".join(parts) + ")"
