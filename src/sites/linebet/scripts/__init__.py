"""Linebet debug/probe scripts package.

Each script in this package is a standalone debug / probe tool for the
Linebet scraper. They are NOT part of the runtime — they exist so
operators and next-session agents can:

  * Reproduce captures against the live site
  * Study the real API shape
  * Validate the extractor without a live browser

Run them as modules from the repo root:

    python -m src.sites.linebet.scripts.validate_live
    python -m src.sites.linebet.scripts.probe_profiles
    python -m src.sites.linebet.scripts.deep_probe
    python -m src.sites.linebet.scripts.capture_real_bodies
    python -m src.sites.linebet.scripts.har_export
    python -m src.sites.linebet.scripts.har_replay <input.har> <output.json>

Outputs go to ``/home/z/my-project/download/linebet_*`` (sandbox) or
``./linebet_output/`` (anywhere else) — see ``_output_dir()`` in each
script.
"""
