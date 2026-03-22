#!/usr/bin/env python
# /// script
# requires-python = ">=3.6"
# ///
"""
Platform detection bootstrap for BMAD Crew Advisor.
Determines the shell-invokable python binary by actually testing both commands.

Usage:
  python detect-platform.py
  python3 detect-platform.py

Output (JSON):
  {"os": "Windows", "python_binary": "python", "python_version": "3.14.2"}
"""

import sys
import platform
import json
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import subprocess

os_name = platform.system()
py_version = platform.python_version()

def can_invoke(cmd):
    """Test whether a command name actually works in the shell."""
    try:
        result = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False

# Test shell-invokable names in order of preference
# We are already running inside python, so at least one of these will work.
# We want the shortest name that the shell can find.
if can_invoke("python"):
    binary = "python"
elif can_invoke("python3"):
    binary = "python3"
else:
    # Absolute fallback: use the full executable path that launched this script
    binary = sys.executable

result = {
    "os": os_name,
    "python_binary": binary,
    "python_version": py_version,
}

print(json.dumps(result))
