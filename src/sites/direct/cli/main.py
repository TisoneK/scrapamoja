#!/usr/bin/env python3
"""Direct API CLI main entry point.

Provides command-line interface for making direct HTTP requests
without launching a browser.
"""

import asyncio
import argparse
import json
import sys
from typing import Any, Set, Type

import httpx

from src.network.direct_api import AsyncHttpClient, AuthConfig
from src.network.errors import NetworkError
from src.core.logging_config import JsonLoggingConfigurator


class DirectCLI:
    """Main CLI class for Direct API scraper."""

    def __init__(self) -> None:
        """Initialize the Direct CLI."""
        self.client: AsyncHttpClient | None = None

    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            prog="direct-cli",
            description="Direct API HTTP client CLI - Make HTTP requests without a browser",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s https://api.example.com
  %(prog)s https://api.example.com --method POST --body '{"key": "value"}'
  %(prog)s https://api.example.com --headers '{"Authorization": "Bearer token"}'
  %(prog)s https://api.example.com --auth-type bearer --auth-token mytoken
  %(prog)s https://api.example.com --verbose
            """
        )

        # Required URL argument
        parser.add_argument(
            "url",
            type=str,
            help="URL to request"
        )

        # HTTP method
        parser.add_argument(
            "--method", "-m",
            type=str,
            default="GET",
            choices=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
            help="HTTP method (default: GET)"
        )

        # Headers
        parser.add_argument(
            "--headers", "-H",
            type=str,
            default="{}",
            help="HTTP headers as JSON string (default: {})"
        )

        # Request body
        parser.add_argument(
            "--body", "-d",
            type=str,
            default=None,
            help="Request body content"
        )

        # JSON body (shorthand)
        parser.add_argument(
            "--json", "-j",
            type=str,
            default=None,
            help="Request body as JSON string"
        )

        # Query parameters
        parser.add_argument(
            "--params", "-p",
            type=str,
            default="{}",
            help="Query parameters as JSON string (default: {})"
        )

        # Timeout
        parser.add_argument(
            "--timeout", "-t",
            type=float,
            default=30.0,
            help="Request timeout in seconds (default: 30)"
        )

        # Authentication - type
        parser.add_argument(
            "--auth-type",
            type=str,
            choices=["bearer", "basic", "cookie"],
            default=None,
            help="Authentication type"
        )

        # Authentication - token
        parser.add_argument(
            "--auth-token",
            type=str,
            default=None,
            help="Bearer token for authentication"
        )

        # Authentication - username
        parser.add_argument(
            "--auth-user",
            type=str,
            default=None,
            help="Username for basic authentication"
        )

        # Authentication - password
        parser.add_argument(
            "--auth-pass",
            type=str,
            default=None,
            help="Password for basic authentication"
        )

        # Authentication - cookie
        parser.add_argument(
            "--auth-cookie",
            type=str,
            default=None,
            help="Cookie string for authentication (format: key=value)"
        )

        # Output format
        parser.add_argument(
            "--output", "-o",
            type=str,
            choices=["json", "text", "raw", "status"],
            default="json",
            help="Output format (default: json)"
        )

        # Pretty print JSON
        parser.add_argument(
            "--pretty", "-P",
            action="store_true",
            help="Pretty print JSON output"
        )

        # Include headers in output
        parser.add_argument(
            "--include-headers",
            action="store_true",
            help="Include response headers in output"
        )

        # Silent mode
        parser.add_argument(
            "--silent", "-s",
            action="store_true",
            help="Suppress all output except the response"
        )

        # Verbose mode
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose logging with credential warnings"
        )

        return parser

    async def run(
        self,
        args: argparse.Namespace,
        interrupt_handler: Any = None,
        shutdown_coordinator: Any = None
    ) -> int:
        """Run CLI with given arguments."""
        try:
            # Initialize logging
            verbose = getattr(args, "verbose", False)
            JsonLoggingConfigurator.setup(verbose=verbose)

            # Parse headers
            try:
                headers = json.loads(args.headers)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid headers JSON: {e}", file=sys.stderr)
                return 1

            # Parse params
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid params JSON: {e}", file=sys.stderr)
                return 1

            # Determine body content
            body = args.body
            if args.json is not None:
                body = args.json
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"

            # Build authentication
            auth = None
            if args.auth_type is not None:
                if args.auth_type == "bearer":
                    if not args.auth_token:
                        print("Error: --auth-token required for bearer auth", file=sys.stderr)
                        return 1
                    auth = AuthConfig(bearer=args.auth_token, auto_source=False)
                elif args.auth_type == "basic":
                    if not args.auth_user or not args.auth_pass:
                        print("Error: --auth-user and --auth-pass required for basic auth", file=sys.stderr)
                        return 1
                    auth = AuthConfig(basic=(args.auth_user, args.auth_pass), auto_source=False)
                elif args.auth_type == "cookie":
                    if not args.auth_cookie:
                        print("Error: --auth-cookie required for cookie auth", file=sys.stderr)
                        return 1
                    # Parse cookie string (key=value)
                    try:
                        key, value = args.auth_cookie.split("=", 1)
                        auth = AuthConfig(cookie={key: value}, auto_source=False)
                    except ValueError:
                        print("Error: --auth-cookie must be in format key=value", file=sys.stderr)
                        return 1
            else:
                # Auto-source from environment variables
                auth = AuthConfig(auto_source=True)

            # Create HTTP client and execute request
            async with AsyncHttpClient() as client:
                # Build request
                method = args.method.upper()
                request_builder = getattr(client, method.lower())(args.url)

                # Add headers
                for key, value in headers.items():
                    request_builder = request_builder.header(key, value)

                # Add query params
                for key, value in params.items():
                    request_builder = request_builder.param(key, value)

                # Add body if present
                if body is not None:
                    request_builder = request_builder.body(body)

                # Add auth if present
                if auth is not None:
                    # Extract auth config for the request builder
                    if auth.bearer:
                        request_builder = request_builder.auth(bearer=auth.bearer)
                    elif auth.basic:
                        request_builder = request_builder.auth(basic=auth.basic)
                    elif auth.cookie:
                        request_builder = request_builder.auth(cookie=auth.cookie)

                # Set timeout
                request_builder = request_builder.timeout(args.timeout)

                # Execute request
                result = await request_builder.execute()

                # Handle NetworkError
                if isinstance(result, NetworkError):
                    if not args.silent:
                        print(f"Error: {result.detail}", file=sys.stderr)
                        if result.status_code:
                            print(f"Status Code: {result.status_code}", file=sys.stderr)
                    return 1

                response, metadata = result

                # Output response
                return self._output_response(
                    response,
                    metadata,
                    args,
                    not args.silent
                )

        except KeyboardInterrupt:
            print("\nOperation interrupted", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            if getattr(args, "verbose", False):
                import traceback
                traceback.print_exc()
            return 1

    def _output_response(
        self,
        response: httpx.Response,
        metadata: Any,
        args: argparse.Namespace,
        show_info: bool
    ) -> int:
        """Output the response in the requested format."""
        output_format = args.output

        if output_format == "status":
            # Just output status code
            print(response.status_code)
            return 0

        # Build response data
        data: dict[str, Any] = {
            "status_code": response.status_code,
            "url": str(response.url),
        }

        # Include headers if requested
        if args.include_headers:
            data["headers"] = dict(response.headers)

        # Add body based on content type
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data["body"] = response.json()
            except Exception:
                data["body"] = response.text
        elif "text" in content_type:
            data["body"] = response.text
        else:
            # Binary or other content - output as base64 or raw
            try:
                data["body"] = response.text
            except Exception:
                data["body"] = response.content.hex()

        # Print response
        if output_format == "json":
            indent = 2 if args.pretty else None
            print(json.dumps(data, indent=indent, ensure_ascii=False))
        elif output_format == "text":
            print(data["body"])
        elif output_format == "raw":
            print(response.content)

        return 0


async def main() -> int:
    """Main CLI entry point."""
    cli = DirectCLI()
    parser = cli.create_parser()
    args = parser.parse_args()
    return await cli.run(args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
