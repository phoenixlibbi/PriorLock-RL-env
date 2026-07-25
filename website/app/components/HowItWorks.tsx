const steps = [
  {
    num: "01",
    title: "Wrap any Harbor task",
    body: "One command injects a synthetic library, in-container docs, a sub-task, and a grader into an existing Terminal-Bench task. The author writes nothing.",
  },
  {
    num: "02",
    title: "Docs are authoritative",
    body: "A generated CHANGELOG documents every behavioural change plainly. Reading it is always sufficient to score 1.0. There is no puzzle — the only way to fail is to not look.",
  },
  {
    num: "03",
    title: "Visible tests don't discriminate",
    body: "Smoke tests assert container types and key presence only. Both the prior-locked and doc-reading solutions pass them, so agents can't use test results to detect anything.",
  },
  {
    num: "04",
    title: "The verifier reads call arguments",
    body: "Grading re-executes the submission against a pristine, verifier-owned copy of the library and recovers the arguments actually supplied. Not output-diffing — direct observation.",
  },
  {
    num: "05",
    title: "Two scores come out",
    body: "task_score from the task's original verifier, untouched. gap_score from the probes. Harbor reads reward.txt or reward.json; the composite emits both, so wrapping is transparent to the runner.",
  },
  {
    num: "06",
    title: "Ten gates prove it offline",
    body: "Before any model runs, the harness verifies gold=1.0, familiar=0.40, stub=0.0, bypass=0.0, tamper-detection, per-probe discrimination, and that the host verifier survived. No Docker, no API key.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="section">
      <p className="section-label">Mechanism</p>
      <h2 className="section-title">
        How it <span>works</span>
      </h2>
      <p className="section-lead">
        PriorLock isolates a single failure mode: agents that trust memorized knowledge
        over in-environment documentation. It rides along on top of whatever the task
        already measured.
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {steps.map((s) => (
          <div key={s.num} className="card flex h-full flex-col p-6">
            <p
              className="mb-3 font-mono text-xs font-bold tracking-[0.14em] uppercase"
              style={{ color: "var(--accent)" }}
            >
              Step {s.num}
            </p>
            <h3 className="mb-2 text-[15px] font-semibold tracking-tight">{s.title}</h3>
            <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
              {s.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
