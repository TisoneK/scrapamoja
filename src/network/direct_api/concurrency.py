"""Concurrent request execution utilities.

This module provides the gather_requests function for executing
multiple HTTP requests concurrently.
"""

import asyncio

import httpx

from src.network.errors import NetworkError, Retryable
from src.network.direct_api.prepared_request import PreparedRequest


async def gather_requests(
    *requests: PreparedRequest,
) -> list[httpx.Response | NetworkError]:
    """Execute multiple requests concurrently using asyncio.gather().

    This function executes all provided PreparedRequest objects concurrently,
    respecting per-domain rate limiting across all requests.

    Args:
        *requests: Variable number of PreparedRequest objects to execute

    Returns:
        list[httpx.Response | NetworkError]: List of responses in the same order
            as the input requests. If a request fails, the corresponding position
            contains a NetworkError model instance rather than raising an exception.
            This allows partial success handling - some requests may succeed while
            others fail.

    Note:
        If the calling task is cancelled, in-flight requests will continue running
        to completion rather than being cancelled immediately.
    """
    if not requests:
        return []

    async def execute_with_error_handling(
        request: PreparedRequest,
        index: int,
    ) -> tuple[int, httpx.Response | NetworkError]:
        """Execute a single request with error handling, returning index and result."""
        try:
            response = await request.execute()
            return (index, response)
        except asyncio.CancelledError:
            # Don't convert CancelledError to NetworkError - let it propagate
            # so the caller knows the request was cancelled
            raise
        except httpx.HTTPError as e:
            # Extract status code if available (use getattr for type safety)
            status_code = None
            response = getattr(e, "response", None)
            if response is not None:
                status_code = response.status_code
            # Create NetworkError for HTTP errors
            error = NetworkError(
                module="direct_api",
                operation=request._method.lower(),
                url=request._url,
                status_code=status_code,
                detail=str(e),
                retryable=Retryable.RETRYABLE,
            )
            return (index, error)
        except Exception as e:
            # Create NetworkError for other errors
            error = NetworkError(
                module="direct_api",
                operation=request._method.lower(),
                url=request._url,
                detail=str(e),
                retryable=Retryable.TERMINAL,
            )
            return (index, error)

    # Execute all requests concurrently with return_exceptions=True to handle
    # partial failures gracefully (but not CancelledError - we want that to propagate)
    results = await asyncio.gather(
        *[execute_with_error_handling(req, i) for i, req in enumerate(requests)],
        return_exceptions=True,
    )

    # Process results - convert any unexpected exceptions to NetworkError
    processed_results: list[tuple[int, httpx.Response | NetworkError]] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Handle any unexpected exceptions (shouldn't happen due to error handling above)
            if isinstance(result, asyncio.CancelledError):
                # Re-raise CancelledError to signal cancellation to caller
                raise result
            error = NetworkError(
                module="direct_api",
                operation="gather",
                url=None,
                detail=str(result),
                retryable=Retryable.TERMINAL,
            )
            processed_results.append((i, error))
        elif isinstance(result, tuple):
            processed_results.append(result)

    # Sort by index to maintain original order
    processed_results.sort(key=lambda x: x[0])

    # Return just the results (not indices)
    return [result for _, result in processed_results]
