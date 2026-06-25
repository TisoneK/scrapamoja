# Direct API Python API Reference

The Direct API module provides a Python interface for making HTTP requests without launching a browser.

## DirectApi Class

```python
from src.network.direct_api import DirectApi
import asyncio

async def main():
    async with DirectApi() as api:
        # GET request
        result = await api.get("https://api.example.com/data")
        
        # POST with JSON
        result = await api.post(
            "https://api.example.com/data",
            json={"name": "test", "value": 123}
        )

asyncio.run(main())
```

## Initialization

```python
api = DirectApi(
    base_url="https://api.example.com",  # Optional base URL
    rate_limit=10.0,                      # Requests per second per domain
    rate_capacity=10.0,                    # Maximum tokens per domain
    auth=AuthConfig(...),                 # Authentication config
    timeout=30.0,                         # Default timeout in seconds
    output=OutputFormat.JSON,            # Default output format
    pretty=False,                         # Pretty print JSON
    include_headers=False,                # Include response headers
    verbose=False                         # Enable verbose logging
)
```

## HTTP Methods

All standard HTTP methods are supported:

- `api.get(url, ...)`
- `api.post(url, ...)`
- `api.put(url, ...)`
- `api.delete(url, ...)`
- `api.patch(url, ...)`
- `api.head(url, ...)`
- `api.options(url, ...)`

## Method Parameters

Each method supports:

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | str | URL to request |
| `headers` | dict | HTTP headers |
| `params` | dict | Query parameters |
| `body` | str/bytes | Request body |
| `json_data` | dict | JSON request body |
| `timeout` | float | Request timeout |
| `auth_config` | AuthConfig | Authentication |
| `output` | OutputFormat | Output format |
| `pretty` | bool | Pretty print JSON |
| `include_headers` | bool | Include response headers |

## Output Formats

```python
from src.network.direct_api import OutputFormat

# JSON (default) - Returns dict with status_code, url, body
result = await api.get("https://api.example.com", output=OutputFormat.JSON)
# {'status_code': 200, 'url': 'https://...', 'body': {...}}

# TEXT - Returns just the response body as string
result = await api.get("https://api.example.com", output=OutputFormat.TEXT)
# "Hello World"

# RAW - Returns raw httpx.Response object
result = await api.get("https://api.example.com", output=OutputFormat.RAW)
# <httpx.Response ...>

# STATUS - Returns just the status code as integer
result = await api.get("https://api.example.com", output=OutputFormat.STATUS)
# 200
```

## Authentication

```python
from src.network.direct_api import DirectApi, AuthConfig

# Bearer token
api = DirectApi(auth=DirectApi.create_auth_config(bearer="mytoken"))

# Basic auth
api = DirectApi(auth=DirectApi.create_auth_config(basic=("user", "pass")))

# Cookie auth
api = DirectApi(auth=DirectApi.create_auth_config(cookie={"session": "abc123"}))

# Auto-source from environment variables (default)
api = DirectApi(auth=AuthConfig(auto_source=True))
```

## Context Manager

The `DirectApi` class must be used as an async context manager:

```python
async with DirectApi() as api:
    result = await api.get("https://api.example.com")
# Client is automatically closed
```

## Error Handling

```python
from src.network.direct_api import DirectApi
from src.network.errors import NetworkError

async with DirectApi() as api:
    result = await api.get("https://api.example.com")
    
    if isinstance(result, NetworkError):
        print(f"Error: {result.detail}")
        print(f"Status: {result.status_code}")
```

## CLI Comparison

The Python API provides feature parity with the Direct CLI. Here's a mapping:

| CLI Argument | Python API Parameter |
|--------------|---------------------|
| `--method/-m` | Method parameter |
| `--headers/-H` | `headers` dict |
| `--body/-d` | `body` parameter |
| `--json/-j` | `json_data` dict |
| `--params/-p` | `params` dict |
| `--timeout/-t` | `timeout` parameter |
| `--auth-type` | `AuthConfig` type |
| `--output/-o` | `output` parameter |
| `--pretty/-P` | `pretty` bool |
| `--include-headers` | `include_headers` bool |
| `--verbose/-v` | `verbose` bool |

## Full Example

```python
import asyncio
from src.network.direct_api import DirectApi, OutputFormat

async def main():
    # Create API instance with custom settings
    async with DirectApi(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=30.0,
        output=OutputFormat.JSON,
        pretty=True,
        verbose=True
    ) as api:
        
        # GET request
        posts = await api.get("/posts/1")
        print(f"Status: {posts['status_code']}")
        print(f"Body: {posts['body']}")
        
        # POST with JSON body
        new_post = await api.post(
            "/posts",
            json={
                "title": "Test Post",
                "body": "This is a test",
                "userId": 1
            }
        )
        
        # With headers
        result = await api.get(
            "/posts",
            headers={"Authorization": "Bearer token"},
            params={"userId": "1"}
        )

asyncio.run(main())
```
