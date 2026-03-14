"""Direct API HTTP client module (SCR-001).

This module provides an async HTTP client with a chainable request builder
for making requests without launching a browser.

## Raw Response Pattern with Metadata

This module returns raw httpx.Response objects paired with ResponseMetadata -
never decoded, never wrapped. This allows calling modules (SCR-004, SCR-005,
site modules) to decide how to handle the content while also receiving
timestamp metadata for data freshness decisions (FR28).

Returns:
    tuple[httpx.Response, ResponseMetadata]: The response object paired with
    metadata containing timestamp for data freshness decisions.
    
Example usage::

    client = AsyncHttpClient()
    response, metadata = await client.get("https://api.example.com").execute()
    
    # Caller decides how to parse:
    data = response.json()  # if JSON
    text = response.text    # if HTML/text
    content = response.content  # raw bytes
    
    # Access timestamp for data freshness decisions:
    if metadata.timestamp:
        print(f"Response timestamp: {metadata.timestamp}")

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
from src.network.direct_api.metadata import ResponseMetadata
from src.network.direct_api.wrapper import DirectApi, OutputFormat

__all__ = [
    "AsyncHttpClient",
    "PreparedRequest",
    "gather_requests",
    "AuthConfig",
    "HttpResponseProtocol",
    "RequestBuilderProtocol",
    "ResponseMetadata",
    "DirectApi",
    "OutputFormat",
]
