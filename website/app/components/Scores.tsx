const scores = [
  {
    value: "0.0",
    name: "Stub / crash",
    desc: "Agent didn't implement anything, or the pipeline threw an exception.",
    bg: "rgba(139,148,158,0.08)",
    border: "var(--border)",
    color: "var(--muted)",
    key: "stub",
  },
  {
    value: "0.40",
    name: "Prior-locked",
    desc: "Correct code structure, familiar semantics. Agent trusted memory, not the installed library.",
    bg: "rgba(248,81,73,0.08)",
    border: "rgba(248,81,73,0.3)",
    color: "var(--red)",
    key: "fam",
  },
  {
    value: "1.0",
    name: "Prior-aware",
    desc: "Read CHANGELOG.md, understood the installed version's behavior, produced the right output.",
    bg: "rgba(63,185,80,0.08)",
    border: "rgba(63,185,80,0.3)",
    color: "var(--green)",
    key: "gold",
  },
];

export default function Scores() {
  return (
    <section id="scores" className="py-18 px-8 max-w-5xl mx-auto">
      <h2 className="font-mono text-2xl font-bold mb-3">
        Score <span style={{ color: "var(--muted)", fontWeight: 400 }}>breakdown</span>
      </h2>
      <p className="text-sm mb-10 max-w-xl" style={{ color: "var(--muted)" }}>
        The 0.40 familiar baseline is the key number — it's a model-free OOD proxy
        proving the gap is prior-dependent.
      </p>

      <div className="grid sm:grid-cols-3 gap-3 mb-6">
        {scores.map((s) => (
          <div
            key={s.key}
            className="rounded-xl p-6 text-center border"
            style={{ background: s.bg, borderColor: s.border }}
          >
            <span className="font-mono text-4xl font-extrabold block mb-2"
              style={{ color: s.color }}>
              {s.value}
            </span>
            <p className="font-semibold text-sm mb-1">{s.name}</p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {s.desc}
            </p>
          </div>
        ))}
      </div>

      <div
        className="rounded-xl p-5 border text-sm leading-relaxed"
        style={{
          background: "rgba(88,166,255,0.06)",
          borderColor: "rgba(88,166,255,0.2)",
          color: "var(--muted)",
        }}
      >
        <strong style={{ color: "var(--text)" }}>Why TB can&apos;t measure this:</strong>{" "}
        On a Terminal-Bench task, a score of 0.40 could mean the task was hard, the model
        was weak, or it got tripped by wrong priors — you can&apos;t separate them. PriorLock&apos;s
        0.40 familiar baseline <em>proves</em> the code is correct in structure but wrong in
        semantics, isolating exactly the prior-override failure mode.
      </div>
    </section>
  );
}
