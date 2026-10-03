#!/bin/sh
# Run the project's gated test suite on whichever platform this is.
#
# The project's gate-command registry invokes it as
#     git -c 'alias.ledger-gate=!sh tools/gates/pytest.sh' ledger-gate
# so one registry line works everywhere: `git` is on the PATH in the agent shells
# of macOS, Linux and Windows (Git for Windows ships its own `sh`, which a `!`
# alias runs the command through), while the interpreter the project's venv
# created lives in `.venv/bin/` on POSIX and `.venv/Scripts/` on Windows.
#
# Extra arguments are passed to pytest, so a caller can narrow the run
# (`sh tools/gates/pytest.sh -k something`).
set -e

if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then
    PY=.venv/Scripts/python.exe
else
    echo "no project venv found (.venv/bin/python or .venv/Scripts/python.exe)" >&2
    echo "create it first, using the recipe for this machine" >&2
    exit 127
fi

exec "$PY" -m pytest \
    src/sites/betb2b/tests/ \
    src/security/tests/ \
    src/browser/profiles/tests/ \
    --no-cov -q "$@"
