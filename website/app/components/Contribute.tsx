const steps = [
  {
    n: 1,
    title: "Scaffold",
    desc: "One command generates the entire domain skeleton — library stubs, Dockerfile, task files, grade.py, stage0.py.",
    code: `priorlock new-domain mylib
# → mylib-domain/ created with all files pre-wired
# → 12 TODOs to fill in`,
  },
  {
    n: 2,
    title: "Implement deviations",
    desc: "Write the synthetic library in two versions: v2.0 (installed, deviations present) and v1.x (familiar, Stage-0 baseline only).",
    code: `# deviation_spec.yaml
library: mylib
deviations:
  - function: group_by
    familiar: "null keys excluded"
    installed: "null keys → __missing__"
    grade_weight: 0.30`,
  },
  {
    n: 3,
    title: "Pass Stage-0",
    desc: "Run 6 offline gates. G2 (familiar=0.40) is the key one — it proves your deviation is in the confident-but-wrong zone.",
    code: `priorlock stage0 mylib-domain
# G1 gold score       PASS  reward=1.0
# G2 familiar score   PASS  reward=0.40
# G3 stub score       PASS  reward=0.0
# G4 ladder           PASS
# G5 visible tests    PASS
# G6 canary clean     PASS
# ALL GATES PASS`,
  },
  {
    n: 4,
    title: "Submit a PR",
    desc: "CI runs Stage-0 automatically on every PR touching a domain directory. All 6 gates must pass before merge.",
    code: `git add mylib-domain/
git commit -m "feat: add mylib domain"
git push origin my-branch
# → GitHub Actions runs priorlock stage0 mylib-domain
# → PR blocked until all gates pass`,
  },
];

const tips = [
  {
    label: "Good deviation",
    color: "var(--green)",
    bg: "rgba(62,207,142,0.07)",
    border: "rgba(62,207,142,0.25)",
    items: [
      "Familiar API shape — model has strong prior",
      "Silent failure — wrong values, not crashes",
      "Edge-case trigger — null keys, ties, boundary",
      "Documented in CHANGELOG.md inside container",
    ],
  },
  {
    label: "Bad deviation",
    color: "var(--red)",
    bg: "rgba(240,113,120,0.07)",
    border: "rgba(240,113,120,0.25)",
    items: [
      "Changed function signature → NameError",
      "Crash or type error → agent debugs it",
      "Too obscure — no prior exists, gap disappears",
      "Visible test reveals it → non-discriminating rule broken",
    ],
  },
];

export default function Contribute() {
  return (
    <section id="contribute" className="section">
      <p className="section-label">Open Benchmark</p>
      <h2 className="section-title">
        Contribute a <span>domain</span>
      </h2>
      <p className="section-lead">
        Anyone can add a domain in ~30 minutes. You write the synthetic library and
        deviation spec — the engine, CI, and grading infrastructure are already there.
      </p>

      {/* 4-step flow */}
      <div className="mb-12 grid gap-4 sm:grid-cols-2">
        {steps.map((s) => (
          <div key={s.n} className="card flex flex-col gap-4 p-6">
            <div className="flex items-start gap-3">
              <span
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full font-mono text-xs font-bold"
                style={{ background: "var(--accent)", color: "#061018" }}
              >
                {s.n}
              </span>
              <div>
                <p className="font-semibold tracking-tight">{s.title}</p>
                <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                  {s.desc}
                </p>
              </div>
            </div>
            <pre>{s.code}</pre>
          </div>
        ))}
      </div>

      {/* Good vs bad */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        {tips.map((t) => (
          <div
            key={t.label}
            className="rounded-[var(--radius)] border p-5"
            style={{ background: t.bg, borderColor: t.border }}
          >
            <p className="mb-3 font-mono text-xs font-bold uppercase tracking-widest"
              style={{ color: t.color }}>
              {t.label}
            </p>
            <ul className="space-y-1.5">
              {t.items.map((item) => (
                <li key={item} className="flex gap-2 text-xs leading-relaxed"
                  style={{ color: "var(--muted)" }}>
                  <span style={{ color: t.color, flexShrink: 0 }}>
                    {t.label === "Good deviation" ? "✓" : "✗"}
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
