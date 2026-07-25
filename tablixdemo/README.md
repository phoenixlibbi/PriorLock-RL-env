# tablixdemo — PriorLock pattern on a data-science domain

Proof that the PriorLock pattern (stale-prior trap + silent deviation +
non-discriminating visible tests) works on any domain. This demo uses
**tablix v1.4**, a synthetic data-aggregation library, instead of kestrel.

Domain: data science / sales reporting
Library: tablix (never published; synthetic)
Task: analyze transactions.csv, produce a JSON sales summary

## Two silent deviations from v1.3 (familiar) behaviour

| Behaviour | v1.3 / familiar | v1.4 / installed |
|---|---|---|
| `group_by` null keys | silently excluded | collected under `"__missing__"` |
| `top_n` ties | strict cut at n | ALL tied records included |

Both deviations are documented in `docs/CHANGELOG.md` and `docs/api_reference.md`
inside the container. The visible tests pass for BOTH solutions. Only the hidden
verifier (`tests/grade.py`) discriminates.

## Score breakdown

| Group | Weight | What it checks |
|---|---|---|
| core | 0.40 | all 3 output keys present, correct types |
| missing_grp | 0.30 | `"__missing__"` in categorySales + categoryCount with correct values |
| top_n_ties | 0.30 | topProductIds == [3,4,5,8,9] (5 tied products, not 3) |

Gold = 1.0 · Familiar (prior-memory) = 0.40 · Stub = 0.0

## Stage-0 receipt

    cd tablixdemo && python3 scripts/stage0.py

All 6 gates pass: G1 gold=1.0, G2 familiar=0.40, G3 stub=0.0,
G4 ladder monotonic, G5 visible tests pass both paths, G6 oracle files
absent from agent-visible surface.

## Harbor run (needs Docker + harbor installed)

    # Oracle smoke (should give reward 1.0):
    harbor run -p tasks/tablixdemo-0

    # Agent run:
    export ANTHROPIC_API_KEY=<key>
    harbor run -p tasks/tablixdemo-0 -a claude-code -m anthropic/claude-opus-4-8

## Folder layout

    src/tablix/             installed library (v1.4 — deviations present)
    src/tablix_familiar/    v1.3 semantics — Stage-0 baseline only, never shipped
    tasks/tablixdemo-0/
      environment/          Dockerfile + repo (TICKET, data, docs, stub, visible tests)
                            + tablix/ (installed v1.4)
      instruction.md        Harbor instruction
      task.toml             schema 1.3, network_mode no-network
      solution/solve.sh     gold solution (oracle)
      tests/                grade.py, expected.json, canonical tablix + data
                            test.sh writes /logs/verifier/reward.json for harbor
    scripts/stage0.py       offline gate verification (no Docker, no API key)

## Key design notes

- The same `run()` call structure works for both familiar and gold pipelines —
  the divergence is entirely in library semantics, not in the code shape.
  This is the core PriorLock insight: agents write identical-looking code but
  the installed library produces different results.
- Visible tests check only shapes (len >= 3, dict present, types correct).
  Both solutions pass. Only the hidden grader checks exact values.
- tablix_familiar never enters the agent container; agents cannot discover
  the deviation by importing and comparing library versions.
