import CodeBlock from "./CodeBlock";

const layers = [
  {
    id: "host",
    title: "Host evaluator",
    score: "task_score",
    body: "The Harbor task’s original verifier checks required outputs, schemas, and protocol facts. Untouched by wrapping — the same checker the author already trusted.",
    entry: "tests/task_verify.sh",
  },
  {
    id: "probe",
    title: "Probe evaluator",
    score: "gap_score",
    body: "Generated probe_grade.py observes call arguments via Signature.bind against a verifier-owned library copy. Success criteria are installed semantics — not self-reported output.",
    entry: "tests/probe_grade.py",
  },
  {
    id: "gates",
    title: "Anti-cheat gates",
    score: "G5–G8",
    body: "Visible tests stay shape-only. Bypass scores zero. Tampering the agent-visible library cannot change the grade. Offline Stage-0 proves each defence before any model runs.",
    entry: "priorlock stage0",
  },
];

export default function Evaluators() {
  return (
    <section id="evaluators" className="section">
      <p className="section-label">Deterministic reward</p>
      <h2 className="section-title">
        Automated <span>Evaluators</span>
      </h2>
      <p className="section-lead">
        Success criteria map to verifier functions — not model self-report — so every
        reward is objective and reproducible.
      </p>

      <div className="mb-8 grid gap-4 md:grid-cols-3">
        {layers.map((layer) => (
          <div
            key={layer.id}
            className="rounded-[var(--radius)] border p-5"
            style={{
              background: "var(--bg2)",
              borderColor: "var(--border)",
            }}
          >
            <p
              className="mb-1 font-mono text-[11px] font-bold uppercase tracking-wider"
              style={{ color: "var(--accent)" }}
            >
              {layer.score}
            </p>
            <p className="mb-2 text-sm font-semibold tracking-tight">{layer.title}</p>
            <p className="mb-3 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {layer.body}
            </p>
            <p className="font-mono text-[11px]" style={{ color: "var(--muted)" }}>
              {layer.entry}
            </p>
          </div>
        ))}
      </div>

      <CodeBlock
        code={`# Offline probe evaluator — no Docker, no API key
priorlock evaluate tasks/my-task --reference gold
# gap_score 1.0 · every check PASS (override)

priorlock evaluate tasks/my-task -s ./probe_solution.py \\
  --json -o evaluator_report.json

# Host task_score still comes from Harbor:
# harbor run -p tasks/my-task -a terminus-2 -m …`}
      />
    </section>
  );
}
