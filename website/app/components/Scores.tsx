const scores = [
  {
    value: "0.0",
    name: "Stub / crash",
    desc: "Agent didn't implement anything, or the pipeline threw an exception.",
    bg: "rgba(139,155,176,0.08)",
    border: "var(--border)",
    color: "var(--muted)",
    key: "stub",
  },
  {
    value: "0.40",
    name: "Prior-locked",
    desc: "Correct code structure, familiar semantics. Agent trusted memory, not the installed library.",
    bg: "rgba(240,113,120,0.08)",
    border: "rgba(240,113,120,0.32)",
    color: "var(--red)",
    key: "fam",
  },
  {
    value: "1.0",
    name: "Prior-aware",
    desc: "Read CHANGELOG.md, understood the installed version's behavior, produced the right output.",
    bg: "rgba(62,207,142,0.08)",
    border: "rgba(62,207,142,0.32)",
    color: "var(--green)",
    key: "gold",
  },
];

export default function Scores() {
  return (
    <section id="scores" className="section">
      <p className="section-label">Scoring</p>
      <h2 className="section-title">
        Score <span>breakdown</span>
      </h2>
      <p className="section-lead">
        The 0.40 familiar baseline is the key number — it&apos;s a model-free OOD proxy proving
        the gap is prior-dependent.
      </p>

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        {scores.map((s) => (
          <div
            key={s.key}
            className="flex h-full flex-col rounded-[var(--radius)] border p-6 text-center"
            style={{ background: s.bg, borderColor: s.border }}
          >
            <span
              className="mb-2 block font-mono text-4xl font-bold tracking-tight"
              style={{ color: s.color }}
            >
              {s.value}
            </span>
            <p className="mb-2 text-sm font-semibold">{s.name}</p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {s.desc}
            </p>
          </div>
        ))}
      </div>

      <div
        className="rounded-[var(--radius)] border p-5 text-sm leading-relaxed"
        style={{
          background: "rgba(91,156,255,0.06)",
          borderColor: "rgba(91,156,255,0.22)",
          color: "var(--muted)",
        }}
      >
        <strong style={{ color: "var(--text)" }}>Why TB can&apos;t measure this:</strong>{" "}
        On a Terminal-Bench task, a score of 0.40 could mean the task was hard, the model was
        weak, or it got tripped by wrong priors — you can&apos;t separate them. PriorLock&apos;s
        0.40 familiar baseline <em>proves</em> the code is correct in structure but wrong in
        semantics, isolating exactly the prior-override failure mode.
      </div>
    </section>
  );
}
