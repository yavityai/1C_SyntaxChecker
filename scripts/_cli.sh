#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m pip install -e . -q >/dev/null 2>&1 || true
exec "$PYTHON" -m syntaxcheck_mcp.cli "$@"
