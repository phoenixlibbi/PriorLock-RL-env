#!/usr/bin/env bash
# Run once after cloning / first copy to Mac to ensure clean tablix paths.
# Fixes the sandbox artifact where tablix/ was nested inside tablix/.
set -e
TASK="$(cd "$(dirname "$0")/.." && pwd)/tasks/tablixdemo-0"
SRC="$(cd "$(dirname "$0")/.." && pwd)/src/tablix/__init__.py"

for dest in \
  "$TASK/environment/tablix" \
  "$TASK/tests/tablix"; do
  rm -rf "$dest"
  mkdir -p "$dest"
  cp "$SRC" "$dest/__init__.py"
done

echo "tablix paths clean"
echo "Run: python3 scripts/stage0.py"
