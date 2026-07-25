const steps = [
  {
    num: "01",
    title: "Synthetic library installed",
    body: "The agent's container has a library (e.g. tablix v1.4) with silent behavioral deviations from the version the agent likely memorized during training.",
  },
  {
    num: "02",
    title: "Docs are in-container",
    body: "A CHANGELOG.md and api_reference.md inside the repo document the exact deviations. The agent can read them — it just has to choose to.",
  },
  {
    num: "03",
    title: "Visible tests don't discriminate",
    body: "The visible smoke tests pass for both the familiar (memorized) solution and the correct solution. Agents cannot use test results to detect the trap.",
  },
  {
    num: "04",
    title: "Hidden verifier scores the gap",
    body: "After the session ends, Harbor runs the hidden grader against exact expected values. Prior-locked agents score 0.40. Prior-aware agents score 1.0.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-18 px-8 max-w-5xl mx-auto">
      <h2 className="font-mono text-2xl font-bold mb-3">
        How it <span style={{ color: "var(--muted)", fontWeight: 400 }}>works</span>
      </h2>
      <p className="text-sm mb-10 max-w-xl" style={{ color: "var(--muted)" }}>
        PriorLock isolates a single failure mode: agents that trust memorized knowledge
        over in-environment documentation.
      </p>

      <div className="grid sm:grid-cols-2 gap-4">
        {steps.map((s) => (
          <div
            key={s.num}
            className="rounded-xl p-6 border"
            style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
          >
            <p className="font-mono text-xs font-bold tracking-widest uppercase mb-3"
              style={{ color: "var(--accent)" }}>
              Step {s.num}
            </p>
            <h3 className="font-semibold text-sm mb-2">{s.title}</h3>
            <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
              {s.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
