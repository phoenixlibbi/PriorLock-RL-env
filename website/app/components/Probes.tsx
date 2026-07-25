import CodeBlock from "./CodeBlock";

const families = [
  {
    id: "default_flip",
    label: "default_flip",
    count: 6,
    mechanism: "A keyword argument's default value was inverted.",
    signal: "call arguments",
    color: "var(--accent)",
    bg: "rgba(91,156,255,0.07)",
    border: "rgba(91,156,255,0.22)",
    code: `# shipped v2.0 — 1.x default was "first"
dedupe(items, key, keep="last")

dedupe(items, "sku")               # 0.40 prior-locked
dedupe(items, "sku", keep="first") # 1.00 read the docs`,
  },
  {
    id: "value_remap",
    label: "value_remap",
    count: 4,
    mechanism: "An accepted value's meaning was reassigned.",
    signal: "call arguments",
    color: "var(--yellow)",
    bg: "rgba(230,180,74,0.07)",
    border: "rgba(230,180,74,0.24)",
    code: `# "keep" used to mean keep EXISTING
merge(base, patch, on_conflict="keep_right")

on_conflict="keep"      # 0.40 patch wins
on_conflict="keep_left" # 1.00 base wins`,
  },
  {
    id: "result_shape",
    label: "result_shape",
    count: 3,
    mechanism: "The return shape changed; don't sanity-correct it.",
    signal: "output values",
    color: "var(--green)",
    bg: "rgba(62,207,142,0.07)",
    border: "rgba(62,207,142,0.25)",
    code: `# tie-inclusive: may return MORE than k
top_k(records, 3, "amount")

result[:3]              # 0.40 "top 3 means 3"
report all tied records # 1.00 read the docs`,
  },
];

const defences = [
  {
    n: "01",
    title: "The verifier owns the library",
    body: "Grading imports a pristine copy from tests/_plx_lib/, placed first on sys.path. Editing the shipped copy is flagged and changes nothing.",
    gate: "G8",
  },
  {
    n: "02",
    title: "Call arguments are observed",
    body: "Recovered via inspect.Signature.bind, which excludes defaults. There is no trace file to forge and no log the agent can write to.",
    gate: null,
  },
  {
    n: "03",
    title: "Bypassing scores 0.00, not 0.40",
    body: "An agent that reimplements the function never reaches the prior-locked rung. Hand-rolling is strictly worse than calling naively.",
    gate: "G7",
  },
  {
    n: "04",
    title: "Visible tests can't leak",
    body: "Generated from the probe set; they assert container types and key presence only. Gold and familiar solutions both pass them.",
    gate: "G5",
  },
  {
    n: "05",
    title: "Probes rotate per task",
    body: "Selection is seeded on the task ID and library names rotate through a pool of plausible non-existent packages. A leaked answer is worth one task.",
    gate: null,
  },
];

const gates = [
  ["G1", "gold score", "exactly 1.0"],
  ["G2", "familiar score", "exactly 0.40"],
  ["G3", "stub score", "exactly 0.0"],
  ["G4", "strict ladder", "0.0 < 0.40 < 1.0"],
  ["G5", "visible tests", "pass for BOTH paths"],
  ["G6", "canary", "no verifier asset exposed"],
  ["G7", "bypass", "scores 0.0, not 0.40"],
  ["G8", "tamper", "flagged, changes no score"],
  ["G9", "discrimination", "every probe separates"],
  ["G10", "host preserved", "original verifier intact"],
  ["G11", "oracle", "oracle scores 1.0 on probes"],
];

export default function Probes() {
  return (
    <section id="probes" className="section">
      <p className="section-label">Zero-effort injection</p>
      <h2 className="section-title">
        You don&apos;t write the <span>deviation</span>
      </h2>
      <p className="section-lead">
        Probes are pre-calibrated units drawn from a catalog and injected automatically.
        Point PriorLock at any Harbor task and it generates the synthetic library, the
        in-container docs, the sub-task, and the grader. The task author writes nothing
        and never hears the word &ldquo;deviation&rdquo;.
      </p>

      {/* one command */}
      <div className="card mb-12 p-6">
        <CodeBlock
          code={`$ priorlock wrap tasks/my-task

✓ my-task wrapped
  library  datawright
  probes   tie_inclusive_topk (result_shape), null_key_policy (default_flip),
           merge_precedence_remap (value_remap)
  weights  task=0.5 gap=0.5
  14 files created, 2 modified

  next: priorlock stage0 tasks/my-task`}
        />
      </div>

      {/* the ladder */}
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
          Every probe scores on three rungs <em>by construction</em>, not by per-domain
          calibration. That is the whole reason this scales: the 0.40 baseline is now a
          property of the harness, verified offline by gate G2 for every wrapped task.
        </p>

        <div className="grid gap-3 sm:grid-cols-3">
          {[
            { s: "0.00", v: "bypassed", d: "never called the library", c: "var(--red)" },
            { s: "0.40", v: "prior_locked", d: "applied the memorized default", c: "var(--yellow)" },
            { s: "1.00", v: "override", d: "read the CHANGELOG and acted", c: "var(--green)" },
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

      {/* three families */}
      <p className="section-label mt-16">Catalog</p>
      <h2 className="section-title">
        Three probe <span>families</span>
      </h2>
      <p className="section-lead">
        Thirteen archetypes across five categories. Selection enforces one probe from each
        family — an agent that learns to always pass keyword arguments explicitly defeats
        <code> default_flip</code> and still fails <code>result_shape</code>.
      </p>

      <div className="mb-12 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {families.map((f) => (
          <div
            key={f.id}
            className="flex min-w-0 flex-col gap-4 overflow-hidden rounded-[var(--radius)] border p-5"
            style={{ background: f.bg, borderColor: f.border }}
          >
            <div className="flex items-baseline justify-between gap-3">
              <p className="font-mono text-sm font-bold" style={{ color: f.color }}>
                {f.label}
              </p>
              <span className="font-mono text-xs" style={{ color: "var(--muted)" }}>
                {f.count} probes
              </span>
            </div>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {f.mechanism}
            </p>
            <CodeBlock code={f.code} preClassName="!text-[11px]" />
            <p className="mt-auto font-mono text-[11px]" style={{ color: "var(--muted)" }}>
              signal read from <span style={{ color: f.color }}>{f.signal}</span>
            </p>
          </div>
        ))}
      </div>

      {/* anti-hacking */}
      <p className="section-label mt-16">Robustness</p>
      <h2 className="section-title">
        Why it can&apos;t be <span>farmed</span>
      </h2>
      <p className="section-lead">
        Five independent defences. Two of them are enforced as gates, so a task that loses
        a defence cannot merge.
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

      {/* gates */}
      <p className="section-label mt-16">Verification</p>
      <h2 className="section-title">
        Eleven offline <span>gates</span>
      </h2>
      <p className="section-lead">
        No Docker, no network, no API key. Every gate runs the <em>generated</em> grader
        against <em>generated</em> reference solutions, so it validates the artefact that
        will actually run in the container.
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

G1 gold score              PASS  1.0
G2 familiar score          PASS  0.4
G3 stub score              PASS  0.0
G4 strict ladder           PASS  0.0 < 0.4 < 1.0
G5 visible tests           PASS  gold=pass familiar=pass
G6 canary clean            PASS  no oracle assets
G7 bypass scores zero      PASS  verdicts={bypassed: 3}
G8 tamper-proof grading    PASS  flags=[library_modified]
G9 all probes discriminate PASS

ALL GATES PASS`}
          />
        </div>
      </div>
      <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
        CI runs all 13 archetypes through all 11 gates on every commit, plus every
        wrapped task and every authored domain in the repo.
      </p>
    </section>
  );
}
