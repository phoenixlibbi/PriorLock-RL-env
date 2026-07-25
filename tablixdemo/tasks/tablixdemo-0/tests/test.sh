#!/bin/bash
# Harbor verifier entrypoint — runs from /tests after agent session ends.
# Phase A: execute agent pipeline.py with canonical tablix + data (no oracle visible).
# Phase B: score report.json vs expected.json.
# Harbor reads /logs/verifier/reward.json.
set -uo pipefail
mkdir -p /logs/verifier
python3 /tests/grade.py --submission /app/repo --tests-dir /tests \
  > /logs/verifier/grade_details.json 2>/logs/verifier/grade_stderr.log
python3 - <<'PY'
import json
d = json.load(open("/logs/verifier/grade_details.json"))
json.dump({"reward": d["reward"]}, open("/logs/verifier/reward.json", "w"))
print("reward", d["reward"], "strict", d["strict_pass"], "reason", d["reason"])
PY
