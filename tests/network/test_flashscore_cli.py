"""Unit tests for the Flashscore CLI entry point + parser.

Regression guard for the bug where `python -m src.sites.flashscore.cli`
crashed with `AttributeError: 'list' object has no attribute 'config'`:
the package `__main__.py` passed raw `sys.argv[1:]` (a list) to
`FlashscoreCLI.run()`, which expects a parsed `argparse.Namespace`
(it reads `args.config` / `args.verbose`). The fix parses first.
"""

import argparse
import ast
import inspect

import pytest

import src.sites.flashscore.cli.__main__ as fs_main
from src.sites.flashscore.cli.main import FlashscoreCLI


@pytest.mark.unit
class TestFlashscoreCLIParser:
    def test_parser_parses_scrape_into_namespace(self) -> None:
        cli = FlashscoreCLI()
        parser = cli.create_parser()

        args = parser.parse_args(["scrape", "basketball", "live"])
        assert isinstance(args, argparse.Namespace)
        assert args.command == "scrape"
        assert args.sport == "basketball"
        assert args.status == "live"
        # run() reads these — they must exist on the Namespace.
        assert hasattr(args, "config")
        assert hasattr(args, "verbose")

    def test_parser_requires_command(self) -> None:
        cli = FlashscoreCLI()
        parser = cli.create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parser_rejects_unknown_sport(self) -> None:
        cli = FlashscoreCLI()
        parser = cli.create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["scrape", "cricket", "live"])


@pytest.mark.unit
class TestFlashscoreEntryPoint:
    def test_main_parses_before_calling_run(self) -> None:
        """The __main__ entry point must parse argv into a Namespace before
        calling run() — not pass the raw list (the original bug)."""
        src = inspect.getsource(fs_main.main)
        tree = ast.parse(src.strip())

        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        names = {
            n.func.attr for n in calls
            if isinstance(n.func, ast.Attribute)
        }
        # It must build a parser and parse args before run().
        assert "create_parser" in names, "entry point must call create_parser()"
        assert "parse_args" in names, "entry point must call parse_args()"

        # run() must NOT be called directly with sys.argv (the raw list).
        for n in calls:
            if isinstance(n.func, ast.Attribute) and n.func.attr == "run":
                for arg in n.args:
                    is_argv = (
                        isinstance(arg, ast.Subscript)
                        and isinstance(arg.value, ast.Attribute)
                        and arg.value.attr == "argv"
                    )
                    assert not is_argv, "run() must receive parsed args, not sys.argv"
