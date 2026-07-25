const steps = [
  {
    n: 1,
    label: "Clone and install the package",
    code: `git clone https://github.com/phoenixlibbi/PriorLock-RL-env
cd PriorLock-RL-env
pip install -e .
# verify
priorlock info`,
  },
  {
    n: 2,
    label: "Run Stage-0 offline gates (no Docker, no API key)",
    code: `priorlock stage0 tablixdemo
# G1 gold score       PASS  reward=1.0
# G2 familiar score   PASS  reward=0.40
# G3 stub score       PASS  reward=0.0
# G4 ladder           PASS  0.0 < 0.40 < 1.0
# G5 visible tests    PASS  gold=pass familiar=pass
# G6 canary clean     PASS  leaks=[]
# ALL GATES PASS`,
  },
  {
    n: 3,
    label: "Run the oracle smoke test (Harbor + Docker required)",
    code: `cd tablixdemo
harbor trial start -p tasks/tablixdemo-0
# reward should be 1.0`,
  },
  {
    n: 4,
    label: "Run an agent (requires ANTHROPIC_API_KEY)",
    code: `export ANTHROPIC_API_KEY=sk-...
harbor trial start -p tasks/tablixdemo-0 \\
  -a claude-code -m anthropic/claude-sonnet-4-5
# Results saved to trials/`,
  },
];

export default function Quickstart() {
  return (
    <section id="quickstart" className="section">
      <p className="section-label">Setup</p>
      <h2 className="section-title">Quickstart</h2>
      <p className="section-lead">
        Requires Python ≥3.10 and{" "}
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
              <pre>{s.code}</pre>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
