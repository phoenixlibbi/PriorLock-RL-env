#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
if [ -f /app/src/hello.txt ] && grep -qx 'ok' /app/src/hello.txt; then
  echo 1.0 > /logs/verifier/reward.txt
  echo '{"reward": 1.0}' > /logs/verifier/reward.json
else
  echo 0.0 > /logs/verifier/reward.txt
  echo '{"reward": 0.0}' > /logs/verifier/reward.json
fi
