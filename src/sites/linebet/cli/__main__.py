"""Entry point for ``python -m src.sites.linebet.cli``."""

import asyncio
import sys
import warnings


async def main() -> int:
    from .main import LinebetCLI
    cli = LinebetCLI()
    return await cli.run(sys.argv[1:])


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    sys.exit(asyncio.run(main()))
