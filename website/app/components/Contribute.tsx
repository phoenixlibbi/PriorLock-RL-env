import CodeBlock from "./CodeBlock";

const paths = [
  {
    tag: "Most common",
    tagColor: "var(--green)",
    tagBg: "rgba(62,207,142,0.14)",
    title: "Wrap a task",
    time: "seconds",
    desc: "You have a Harbor task and want it to also measure prior-override capability. Probes are selected automatically. You write nothing.",
    code: `priorlock wrap tasks/my-task
priorlock stage0 tasks/my-task

# whole suites work too
priorlock wrap tasks/ --recursive`,
  },
  {
    tag: "Highest leverage",
    tagColor: "var(--accent)",
    tagBg: "rgba(91,156,255,0.14)",
    title: "Add a probe archetype",
    time: "~1 hour",
    desc: "A new archetype is immediately available to every wrapped task, present and future. One archetype helps everyone; one domain helps one task.",
    code: `# src/priorlock/probes/catalog.py
Probe(
    id="my_probe",
    family="default_flip",
    fn="normalize",
    param="mode",
    gold_kwargs={"mode": "strict"},
    familiar_kwargs={},
    ...
)`,
  },
  {
    tag: "Escape hatch",
    tagColor: "var(--yellow)",
    tagBg: "rgba(230,180,74,0.14)",
    title: "Author a domain",
    time: "~30 min",
    desc: "Only when you need something the catalog can't express — a domain-specific API shape, a multi-step deviation, a non-Python target.",
    code: `priorlock new-domain mylib
# scaffolds mylib-domain/ with all
# files pre-wired and TODOs to fill

priorlock stage0 mylib-domain`,
  },
];

const tips = [
  {
    label: "Good probe archetype",
    color: "var(--green)",
    bg: "rgba(62,207,142,0.07)",
    border: "rgba(62,207,142,0.25)",
    items: [
      "Familiar shape — models have a strong prior about dedupe(items, key)",
      "Silent — wrong values, never a crash or a type error",
      "Documented — reading the CHANGELOG is sufficient to score 1.0",
      "Discriminating — gold output differs from familiar output",
      "Edge-case trigger — null keys, ties, empty input, boundary indices",
    ],
  },
  {
    label: "Bad probe archetype",
    color: "var(--red)",
    bg: "rgba(240,113,120,0.07)",
    border: "rgba(240,113,120,0.25)",
    items: [
      "Changed signature → TypeError, the agent debugs and wins",
      "Genuinely novel API — no prior exists, so nothing to override",
      "A task clause that hints at the deviation",
      "Only reachable on input the agent won't construct",
      "Needs network access or a real published package",
    ],
  },
];

export default function Contribute() {
  return (
    <section id="contribute" className="section">
      <p className="section-label">Open Benchmark</p>
      <h2 className="section-title">
        Three ways to <span>contribute</span>
      </h2>
      <p className="section-lead">
        The engine, catalog, CI, and grading infrastructure are already there. Most
        contributions are one command.
      </p>

      <div className="mb-12 grid gap-4 lg:grid-cols-3">
        {paths.map((p) => (
          <div key={p.title} className="card flex h-full flex-col gap-4 p-6">
            <div className="flex items-center justify-between gap-2">
              <span
                className="rounded-full px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider"
                style={{ background: p.tagBg, color: p.tagColor }}
              >
                {p.tag}
              </span>
              <span className="font-mono text-[11px]" style={{ color: "var(--muted)" }}>
                {p.time}
              </span>
            </div>
            <div>
              <p className="font-semibold tracking-tight">{p.title}</p>
              <p className="mt-1.5 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                {p.desc}
              </p>
            </div>
            <CodeBlock code={p.code} className="mt-auto" preClassName="!text-[11px]" />
          </div>
        ))}
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        {tips.map((t) => (
          <div
            key={t.label}
            className="rounded-[var(--radius)] border p-5"
            style={{ background: t.bg, borderColor: t.border }}
          >
            <p
              className="mb-3 font-mono text-xs font-bold uppercase tracking-widest"
              style={{ color: t.color }}
            >
              {t.label}
            </p>
            <ul className="space-y-1.5">
              {t.items.map((item) => (
                <li
                  key={item}
                  className="flex gap-2 text-xs leading-relaxed"
                  style={{ color: "var(--muted)" }}
                >
                  <span style={{ color: t.color, flexShrink: 0 }}>
                    {t.label.startsWith("Good") ? "✓" : "✗"}
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <a
        href="https://github.com/phoenixlibbi/PriorLock-RL-env/blob/main/CONTRIBUTING.md"
        target="_blank"
        rel="noopener noreferrer"
        className="btn btn-ghost inline-flex"
      >
        Read the full contribution guide →
      </a>
    </section>
  );
}
