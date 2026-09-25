#!/usr/bin/env bash
# Launch the countdown timer on Linux.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo ".venv does not exist. Please run setup (see README)."
    exit 1
fi

exec .venv/bin/python main.py "$@"
