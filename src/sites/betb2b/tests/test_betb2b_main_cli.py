"""Tests for the src.main dispatcher adapter (BetB2BMainCLI).

betb2b now runs via `python -m src.main betb2b …` alongside the other sites.
The dispatcher calls `create_parser()` → `parse_args(argv)` → `run(args,
interrupt_handler=, shutdown_coordinator=)`, which differs from betb2b's own
`run(argv)`. These pin the adapter contract + the SITE_CLIS registration.
"""

from __future__ import annotations

import argparse
import importlib
import inspect

import pytest

from src.sites.betb2b.cli.main import BetB2BCLI, BetB2BMainCLI


def test_registered_in_site_clis():
    from src.main import SITE_CLIS

    assert "betb2b" in SITE_CLIS
    module_path, class_name = SITE_CLIS["betb2b"]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)  # must resolve
    assert cls is BetB2BMainCLI


def test_adapter_matches_dispatcher_contract():
    cli = BetB2BMainCLI()
    # create_parser() → ArgumentParser
    parser = cli.create_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    # run() must accept (args, interrupt_handler=, shutdown_coordinator=)
    sig = inspect.signature(cli.run)
    assert "interrupt_handler" in sig.parameters
    assert "shutdown_coordinator" in sig.parameters
    assert inspect.iscoroutinefunction(cli.run)


def test_parser_round_trips_scrape_args():
    cli = BetB2BMainCLI()
    parser = cli.create_parser()
    args = parser.parse_args(
        ["scrape", "--skin", "linebet", "--sport", "basketball",
         "--action", "list_prematch"]
    )
    assert args.command == "scrape"
    assert args.skin == "linebet"
    assert args.sport == "basketball"
    assert args.action == "list_prematch"


async def test_adapter_dispatches_to_run_args(monkeypatch):
    """run(args) must delegate to the underlying BetB2BCLI.run_args."""
    cli = BetB2BMainCLI()
    args = cli.create_parser().parse_args(["skins"])

    seen = {}

    async def fake_run_args(a):
        seen["args"] = a
        return 0

    monkeypatch.setattr(cli._cli, "run_args", fake_run_args)
    rc = await cli.run(args, interrupt_handler=object(), shutdown_coordinator=object())
    assert rc == 0
    assert seen["args"] is args


async def test_standalone_run_still_parses_argv(monkeypatch):
    """BetB2BCLI.run(argv) (standalone entry point) still parses + dispatches."""
    cli = BetB2BCLI()
    seen = {}

    async def fake_run_args(a):
        seen["cmd"] = a.command
        return 0

    monkeypatch.setattr(cli, "run_args", fake_run_args)
    rc = await cli.run(["skins"])
    assert rc == 0
    assert seen["cmd"] == "skins"


@pytest.mark.parametrize("module", ["src.sites.betb2b.cli",
                                    "src.sites.betb2b.cli.main"])
def test_documented_module_entry_points_actually_run(module):
    """AGENTS.md documents `python -m src.sites.betb2b.cli.main <cmd>`. Without
    a __main__ guard that form imports the module and exits 0 in silence — a
    no-op that reads as success. Both spellings must dispatch."""
    import json
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]
    proc = subprocess.run([sys.executable, "-m", module, "skins"],
                          cwd=repo, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["count"] > 0
