import CodeBlock from "./CodeBlock";

const steps = [
  {
    n: 1,
    label: "Install the CLI (Harbor-style)",
    code: `# recommended — isolated tool, like: uv tool install harbor
uv tool install "priorlock @ git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"

# or with pip:
# pip install "git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"

priorlock --help
priorlock info

# after PyPI publish this becomes simply:
#   uv tool install priorlock
#   pip install priorlock

# contributors only — full tree for local development:
# git clone … && pip install -e ".[dev]"`,
  },
  {
    n: 2,
    label: "Run the oracle first — prove the Harbor task is sound",
    code: `# Before wrapping: ordinary Harbor task must score 1.0
harbor run -p tasks/my-task -a oracle

# Expect: Mean 1.000 · Errors 0 · reward = 1.0
# If this fails, fix the task — don't wrap a broken baseline.

# After wrapping (and for leakprobe): same check
# harbor run -p tasks/my-task -a oracle
# harbor run -p tasks/my-task__leakprobe -a oracle`,
  },
  {
    n: 3,
    label: "Wrap any Harbor task — this is the whole authoring step",
    code: `priorlock preflight tasks/my-task
priorlock wrap tasks/my-task --baseline-from jobs/

# ✓ my-task wrapped
#   library  datawright
#   probes   tie_inclusive_topk (result_shape),
#            null_key_policy (default_flip),
#            merge_precedence_remap (value_remap)
#   weights  task=0.5 gap=0.5

priorlock wrap tasks/ --recursive     # or an entire suite`,
  },
  {
    n: 4,
    label: "Run the twelve offline gates (no Docker, no API key)",
    code: `priorlock stage0 tasks/my-task

# G1 gold score              PASS  1.0
# G2 familiar score          PASS  0.4
# G3 stub score              PASS  0.0
# G4 strict ladder           PASS  0.0 < 0.4 < 1.0
# G5 visible tests           PASS  gold=pass familiar=pass
# G6 canary clean            PASS  no oracle assets
# G7 bypass scores zero      PASS  verdicts={bypassed: 3}
# G8 tamper-proof grading    PASS  flags=[library_modified]
# G9 all probes discriminate PASS
# ALL GATES PASS`,
  },
  {
    n: 5,
    label: "Attack it — 8 cheat classes, pooled FAR receipt",
    code: `priorlock cheats tasks/my-task --suite

# trials          104     8 classes x 13 archetypes
# all executed    104/104 none excluded
# false accepts   0/104   Wilson95 [0.0000, 0.0356]
# required        upper < 0.05                  PASS
# worst surviving 0.0     against a 0.40 baseline
# SOUND`,
  },
  {
    n: 6,
    label: "Inspect what the benchmark actually reads",
    code: `priorlock verify tasks/my-task --reference familiar

# gap_score 0.4
#   merge_precedence_remap   prior_locked   0.40
#     supplied: [{"on_conflict": "keep"}]     ← the 1.x meaning
#     output matches: familiar`,
  },
  {
    n: 7,
    label: "Run an agent (Harbor + Docker + API key)",
    code: `export ANTHROPIC_API_KEY=sk-...
harbor run -p tasks/my-task \\
  -a claude-code -m anthropic/claude-sonnet-5

# reward.json          composite
# priorlock_summary.json   task_score + gap_score + per-probe verdicts`,
  },
  {
    n: 8,
    label: "Measure how informative each probe is for that model",
    code: `priorlock calibrate ingest trials/ --model claude-sonnet-5
priorlock calibrate report --model claude-sonnet-5
priorlock calibrate recommend --model claude-sonnet-5

# calibration tunes RESOLUTION, not validity —
# the 0.40 baseline is structural and gate-verified`,
  },
];

export default function Quickstart() {
  return (
    <section id="quickstart" className="section">
      <p className="section-label">Setup</p>
      <h2 className="section-title">Quickstart</h2>
      <p className="section-lead">
        Requires Python ≥3.10. Step 1 is local-only. Step 2 needs{" "}
        <a
          href="https://harborframework.com"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "var(--accent)" }}
        >
          Harbor
        </a>{" "}
        + Docker (oracle smoke — expect reward 1.0). Steps 3–6 need no API key.
        Step 7 adds a live model.
      </p>

      <div className="flex flex-col gap-5">
        {steps.map((s) => (
          <div key={s.n} className="card flex gap-4 p-5 sm:p-6">
            <div
              className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full font-mono text-xs font-bold"
              style={{ background: "var(--accent)", color: "#061018" }}
            >
              {s.n}
            </div>
            <div className="min-w-0 flex-1">
              <p className="mb-3 text-sm font-medium" style={{ color: "var(--text)" }}>
                {s.label}
              </p>
              <CodeBlock code={s.code} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
