#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 PORT" >&2
  exit 1
fi
exec "$SCRIPT_DIR/_cli.sh" set-port "$1"
