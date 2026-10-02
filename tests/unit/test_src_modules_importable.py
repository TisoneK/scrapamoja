"""Every module under ``src/`` must import.

A repo-wide import sweep found ~100 modules that could not be imported at all: a repeated
keyword argument, names used without their import, wrong relative-import depths, classes
re-exported from nowhere, a FastAPI route declaring a service object as a query parameter.
Most were fixed; ``KNOWN_BROKEN`` lists what still needs a DESIGN decision (a missing class,
module or field), each with the reason. The test fails both ways, so the list cannot rot:

* a module breaks that is not listed  -> fix it (or, if it is deliberately unfinished, list it);
* a listed module starts to import     -> delete it from ``KNOWN_BROKEN``.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# module -> why it cannot be imported yet (all need a design decision, not a typo fix)
KNOWN_BROKEN = {
    "src.browser.authority": "StealthSettings has no 'webgl_protection' field (presets in browser/models/stealth.py use fields that were renamed/never added)",
    "src.browser.configuration": "same StealthSettings 'webgl_protection' mismatch",
    "src.selectors.integration": "imports src.selectors.engine.configuration.*, which does not exist ('engine' is a module, not a package)",
    "src.telemetry.integration.alerting_integration": "ITelemetryIntegration does not exist (only ISelectorTelemetryIntegration)",
}
# (src.sites.flashscore.cli* import the top-level 'tests' package: they only import when the
# working directory is the repo root - fragile, tracked in the backlog, not listed as broken.)
# Setup scripts and entry points that are not meant to be imported.
SKIP = {"src.sites.shared_components.setup"}

SWEEP = r"""
import importlib, json, os, signal, subprocess, sys
os.environ["BETB2B_NO_DOTENV"] = "1"
skip = set(json.loads(sys.argv[1]))
root = sys.argv[2]
files = [f for f in subprocess.check_output(["git", "-C", root, "ls-files", "src/*.py"]).decode().split("\n") if f]
mods = []
for f in files:
    parts = f[:-3].split("/")
    if parts[-1] == "__main__" or "tests" in parts or "scripts" in parts:
        continue
    if parts[-1] == "__init__":
        parts = parts[:-1]
    m = ".".join(parts)
    if m not in skip:
        mods.append(m)
class T(Exception): pass
def h(*a): raise T()
signal.signal(signal.SIGALRM, h)
bad = {}
for m in mods:
    signal.alarm(20)
    try:
        importlib.import_module(m)
    except T:
        bad[m] = "TIMEOUT"
    except BaseException as e:
        bad[m] = f"{type(e).__name__}: {str(e)[:160]}"
    finally:
        signal.alarm(0)
print("RESULT" + json.dumps({"count": len(mods), "bad": bad}))
"""


@pytest.mark.slow
def test_every_src_module_imports_except_the_known_broken_ones(tmp_path):
    # Run from a scratch directory: some modules write default files (e.g. resilience_config.json)
    # into the current directory on import, and the repo root must stay clean.
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proc = subprocess.run([sys.executable, "-c", SWEEP, json.dumps(sorted(SKIP)), str(ROOT)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=600)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("RESULT")), None)
    assert line, f"sweep produced no result:\n{proc.stderr[-800:]}"
    result = json.loads(line[len("RESULT"):])
    bad = result["bad"]
    new = {m: why for m, why in bad.items() if m not in KNOWN_BROKEN}
    fixed = sorted(m for m in KNOWN_BROKEN if m not in bad)
    assert not new, "modules that cannot be imported (fix them, or list them in KNOWN_BROKEN with a reason):\n" + \
        "\n".join(f"  {m}: {w}" for m, w in sorted(new.items()))
    assert not fixed, f"these now import - remove them from KNOWN_BROKEN: {fixed}"
    assert result["count"] > 600          # the sweep really covered the tree
