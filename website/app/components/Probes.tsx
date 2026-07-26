import CodeBlock from "./CodeBlock";

const defences = [
  {
    n: "01",
    title: "Grading uses a verifier-owned library copy",
    body: "Tampering with the agent-visible library cannot change the score.",
    gate: "G8",
  },
  {
    n: "02",
    title: "Scores come from behaviour, not self-report",
    body: "Agents cannot write a log or trace that the grader trusts as ground truth.",
    gate: null,
  },
  {
    n: "03",
    title: "Bypassing is worse than being prior-locked",
    body: "Reimplementing instead of using the shipped library cannot reach the middle rung.",
    gate: "G7",
  },
  {
    n: "04",
    title: "Visible tests do not discriminate the trap",
    body: "Smoke tests both paths can pass; they are not a side channel for the answer.",
    gate: "G5",
  },
  {
    n: "05",
    title: "Probe sets rotate per task",
    body: "Selection is seeded per task so a leaked answer for one instance does not transfer.",
    gate: null,
  },
];

const gates = [
  ["G1", "gold score", "reference upper bound"],
  ["G2", "familiar score", "structural mid rung"],
  ["G3", "stub score", "lower bound"],
  ["G4", "strict ladder", "ordering holds"],
  ["G5", "visible tests", "non-discriminating"],
  ["G6", "canary", "no verifier leak"],
  ["G7", "bypass", "cannot farm mid rung"],
  ["G8", "tamper", "edits do not help"],
  ["G9", "discrimination", "every probe separates"],
  ["G10", "host preserved", "original verifier intact"],
  ["G11", "oracle", "shipped oracle solves probes"],
  ["G12", "canary", "canary never agent-visible"],
];

export default function Probes() {
  return (
    <section id="probes" className="section">
      <p className="section-label">Zero-effort injection</p>
      <h2 className="section-title">
        You don&apos;t write the <span>deviation</span>
      </h2>
      <p className="section-lead">
        Probes are pre-calibrated units drawn from a private catalog and injected
        automatically. Point PriorLock at any Harbor task — it generates the synthetic
        library, in-container docs, sub-task, and grader. Authors never see (or need)
        the probe design notes.
      </p>

      <div className="card mb-12 p-6">
        <CodeBlock
          code={`$ priorlock wrap tasks/my-task

✓ my-task wrapped
  library  <synthetic>
  probes   <selected from catalog>
  weights  task=0.5 gap=0.5
  files created / modified

  next: priorlock stage0 tasks/my-task`}
        />
      </div>

      <div
        className="mb-12 rounded-[var(--radius)] border p-6 sm:p-8"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >
        <p
          className="mb-1 font-mono text-xs font-bold uppercase tracking-widest"
          style={{ color: "var(--accent)" }}
        >
          The structural ladder
        </p>
        <p className="mb-6 text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
          Every probe scores on three rungs <em>by construction</em>. The mid rung is a
          property of the harness, verified offline — not a number tuned per domain.
        </p>

        <div className="grid gap-3 sm:grid-cols-3">
          {[
            { s: "0.00", v: "bypassed", d: "did not use the shipped library", c: "var(--red)" },
            { s: "0.40", v: "prior_locked", d: "trusted memory over the docs", c: "var(--yellow)" },
            { s: "1.00", v: "override", d: "followed environment ground truth", c: "var(--green)" },
          ].map((r) => (
            <div
              key={r.v}
              className="rounded-[10px] border p-4"
              style={{ background: "var(--bg3)", borderColor: "var(--border)" }}
            >
              <span
                className="block font-mono text-2xl font-bold tracking-tight"
                style={{ color: r.c }}
              >
                {r.s}
              </span>
              <p className="mt-1 font-mono text-xs" style={{ color: r.c }}>
                {r.v}
              </p>
              <p className="mt-1.5 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                {r.d}
              </p>
            </div>
          ))}
        </div>
      </div>

      <p className="section-label mt-16">Catalog</p>
      <h2 className="section-title">
        Probe <span>catalog</span>
      </h2>
      <p className="section-lead">
        Sixty-one probes across nine domains. We publish scale and difficulty bands —
        not IDs or pass/fail recipes. For the <em>idea</em>, see the labeled toy example
        in{" "}
        <a href="/#research" style={{ color: "var(--accent)" }}>
          Research
        </a>
        ; for live tasks, the container docs are authoritative.
      </p>

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        {[
          { label: "Domains", value: "9", hint: "coding → frameworks" },
          { label: "Probes", value: "61", hint: "private catalog" },
          { label: "Selection", value: "seeded", hint: "rotates per task" },
        ].map((c) => (
          <div
            key={c.label}
            className="rounded-[var(--radius)] border p-5"
            style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
          >
            <p className="font-mono text-xs font-bold uppercase tracking-widest" style={{ color: "var(--muted)" }}>
              {c.label}
            </p>
            <p className="mt-2 font-mono text-2xl font-bold" style={{ color: "var(--accent)" }}>
              {c.value}
            </p>
            <p className="mt-1 text-xs" style={{ color: "var(--muted)" }}>
              {c.hint}
            </p>
          </div>
        ))}
      </div>

      <div className="mb-12 grid gap-3 sm:grid-cols-3">
        {[
          {
            lvl: "L1",
            title: "Atomic",
            body: "Single-surface units. Isolates one prior-vs-docs conflict.",
          },
          {
            lvl: "L2",
            title: "Coupled",
            body: "Composition across related calls — still domain-local.",
          },
          {
            lvl: "L3",
            title: "Workflow",
            body: "Multi-step paths where skipping docs compounds error.",
          },
        ].map((l) => (
          <div
            key={l.lvl}
            className="rounded-[var(--radius)] border p-5"
            style={{ background: "var(--bg3)", borderColor: "var(--border)" }}
          >
            <p className="font-mono text-xs font-bold" style={{ color: "var(--accent)" }}>
              {l.lvl} · {l.title}
            </p>
            <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {l.body}
            </p>
          </div>
        ))}
      </div>

      <p className="section-label mt-16">Robustness</p>
      <h2 className="section-title">
        Why it can&apos;t be <span>farmed</span>
      </h2>
      <p className="section-lead">
        Independent defences, several enforced as merge-blocking gates. Details that would
        help an attacker are kept out of public docs.
      </p>

      <div
        className="mb-12 overflow-hidden rounded-[var(--radius)] border"
        style={{ borderColor: "var(--border)" }}
      >
        {defences.map((d, i, arr) => (
          <div
            key={d.n}
            className="flex gap-5 p-5 sm:p-6"
            style={{
              background: i % 2 === 0 ? "var(--bg2)" : "var(--bg3)",
              borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : undefined,
            }}
          >
            <span
              className="mt-0.5 flex-shrink-0 font-mono text-xs font-bold"
              style={{ color: "var(--accent)" }}
            >
              {d.n}
            </span>
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold tracking-tight">{d.title}</p>
                {d.gate && (
                  <span
                    className="rounded-full px-2 py-0.5 font-mono text-[10px] font-bold"
                    style={{ background: "rgba(62,207,142,0.14)", color: "var(--green)" }}
                  >
                    gate {d.gate}
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                {d.body}
              </p>
            </div>
          </div>
        ))}
      </div>

      <p className="section-label mt-16">Verification</p>
      <h2 className="section-title">
        Twelve offline <span>gates</span>
      </h2>
      <p className="section-lead">
        No Docker, no network, no API key. Gates validate the generated artefact — not a
        hand-written story about it.
      </p>

      <div className="grid gap-4 lg:grid-cols-2 lg:items-stretch">
        <div className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="gates-table w-full">
              <colgroup>
                <col className="gates-col-id" />
                <col className="gates-col-check" />
                <col className="gates-col-req" />
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">Gate</th>
                  <th scope="col">Check</th>
                  <th scope="col">Requirement</th>
                </tr>
              </thead>
              <tbody>
                {gates.map(([id, check, req]) => (
                  <tr key={id}>
                    <td className="gates-id">{id}</td>
                    <td>{check}</td>
                    <td className="gates-req">{req}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card flex flex-col p-6">
          <CodeBlock
            code={`$ priorlock stage0 tasks/my-task

G1–G12 … PASS
ALL GATES PASS`}
          />
        </div>
      </div>
      <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
        CI runs the catalog and wrapped tasks through the gate suite on every commit.
      </p>
    </section>
  );
}
