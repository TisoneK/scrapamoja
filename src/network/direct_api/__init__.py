"""Direct API HTTP client module (SCR-001).

This module provides an async HTTP client with a chainable request builder
for making requests without launching a browser.
"""

from src.network.direct_api.client import (
    AsyncHttpClient,
    PreparedRequest,
    gather_requests,
)
from src.network.direct_api.interfaces import (
    AuthConfig,
    HttpResponseProtocol,
    RequestBuilderProtocol,
)

__all__ = [
    "AsyncHttpClient",
    "PreparedRequest",
    "gather_requests",
    "AuthConfig",
    "HttpResponseProtocol",
    "RequestBuilderProtocol",
]
