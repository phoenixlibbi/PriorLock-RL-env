import CodeBlock from "./CodeBlock";

const steps = [
  {
    n: 1,
    label: "Install the package",
    code: `git clone https://github.com/phoenixlibbi/PriorLock-RL-env
cd PriorLock-RL-env
pip install -e .

priorlock info      # what's wrapped, what's authored, catalog size`,
  },
  {
    n: 2,
    label: "Wrap any Harbor task — this is the whole authoring step",
    code: `priorlock wrap tasks/my-task

# ✓ my-task wrapped
#   library  datawright
#   probes   tie_inclusive_topk (result_shape),
#            null_key_policy (default_flip),
#            merge_precedence_remap (value_remap)
#   weights  task=0.5 gap=0.5

priorlock wrap tasks/ --recursive     # or an entire suite`,
  },
  {
    n: 3,
    label: "Run the nine offline gates (no Docker, no API key)",
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
    n: 4,
    label: "Inspect what the benchmark actually reads",
    code: `priorlock verify tasks/my-task --reference familiar

# gap_score 0.4
#   merge_precedence_remap   prior_locked   0.40
#     supplied: [{"on_conflict": "keep"}]     ← the 1.x meaning
#     output matches: familiar`,
  },
  {
    n: 5,
    label: "Run an agent (Harbor + Docker + API key)",
    code: `export ANTHROPIC_API_KEY=sk-...
harbor run -p tasks/my-task \\
  -a claude-code -m anthropic/claude-sonnet-5

# reward.json          composite
# priorlock_summary.json   task_score + gap_score + per-probe verdicts`,
  },
  {
    n: 6,
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
        Requires Python ≥3.10. Steps 1–4 need nothing else — no Docker, no network, no
        API key. Step 5 adds{" "}
        <a
          href="https://harborframework.com"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "var(--accent)" }}
        >
          Harbor
        </a>{" "}
        with Docker.
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
