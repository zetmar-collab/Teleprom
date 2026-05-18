#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ -x "$VENV_PYTHON" ]; then
  "$VENV_PYTHON" "$PROJECT_DIR/teleprompter.py"
elif command -v python3 >/dev/null 2>&1; then
  python3 "$PROJECT_DIR/teleprompter.py"
else
  python "$PROJECT_DIR/teleprompter.py"
fi
