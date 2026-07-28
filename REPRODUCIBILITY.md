# Reproducibility

Short checklist so a third party can install PriorLock and validate offline
determinism without reading the whole codebase.

## 1. Install

```bash
git clone https://github.com/phoenixlibbi/PriorLock-RL-env
cd PriorLock-RL-env
pip install -e ".[dev]"
priorlock --version
```

If `priorlock` still prints an old version, you have a stale global CLI
(`uv tool` / earlier `pip install`). Prefer the editable env:

```bash
python -m priorlock.cli --version
# or: hash -r && which priorlock
```

## 2. Pin hash seed

```bash
export PYTHONHASHSEED=0
```

Probe selection and catalog iteration stay stable with this pin. Tests set it
via `tests/conftest.py` as well.

RL train vs eval seeds stay disjoint through
`load_environment(..., seed_prefix=...)` (default prefixes
`plx-train` / `plx-eval`).

## 3. Validate offline

```bash
pytest -q
priorlock evaluate <wrapped-task> --reference gold    # expect gap_score 1.0
priorlock evaluate <wrapped-task> --reference familiar  # expect gap_score 0.40
priorlock stage0 <wrapped-task>                       # twelve offline gates
# optional (slower):
priorlock cheats <wrapped-task> --suite
```

No Docker and no API keys are required for these commands.

## 4. Capture a run fingerprint

```bash
priorlock repro
# → logs/repro/<timestamp>.json
```

Attach that JSON when sharing results. It records PriorLock version, Python,
`PYTHONHASHSEED`, platform, git commit (if available), and probe catalog hash.

Re-run recipe printed by the command:

```bash
export PYTHONHASHSEED=0 && pytest -q && priorlock repro
```

## 5. Harbor path

`task_score` still needs Docker + Harbor (`harbor run …`). The probe half
(`gap_score`, Stage-0, `priorlock evaluate`) is offline-deterministic; CI
runs only that half.
