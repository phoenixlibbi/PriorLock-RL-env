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
    <section id="quickstart" className="py-18 px-8 max-w-5xl mx-auto">
      <h2 className="font-mono text-2xl font-bold mb-3">Quickstart</h2>
      <p className="text-sm mb-10" style={{ color: "var(--muted)" }}>
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
          <div key={s.n} className="flex gap-4">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-extrabold flex-shrink-0 mt-0.5"
              style={{ background: "var(--accent)", color: "#0d1117" }}
            >
              {s.n}
            </div>
            <div className="flex-1">
              <p className="text-sm mb-2" style={{ color: "var(--muted)" }}>{s.label}</p>
              <pre>{s.code}</pre>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
