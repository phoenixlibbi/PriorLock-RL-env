const papers = [
  {
    id: "stale",
    title: "Can LLM Agents Know When Their Memories Are No Longer Valid?",
    authors: "Chen et al.",
    year: "2025",
    venue: "arXiv 2605.06527",
    url: "https://arxiv.org/abs/2605.06527",
    relevance:
      "Demonstrates that agents fail to detect when memorized knowledge conflicts with current context — exactly the failure mode PriorLock is designed to measure.",
  },
  {
    id: "supersede",
    title: "Diagnosing and Training the Memory-Update Gap in LLM Agents",
    authors: "Zhang et al.",
    year: "2025",
    venue: "arXiv 2606.27472",
    url: "https://arxiv.org/abs/2606.27472",
    relevance:
      "Introduces the memory-update gap — the empirical gulf between what an agent has memorized and what the live environment specifies. PriorLock provides a reproducible harness for measuring this gap.",
  },
  {
    id: "cutoff",
    title: "Can Prompts Rewind Time for LLMs? Evaluating the Effectiveness of Prompted Knowledge Cutoffs",
    authors: "Kasner et al.",
    year: "2025",
    venue: "arXiv 2510.02340",
    url: "https://arxiv.org/abs/2510.02340",
    relevance:
      "Shows that prompting an agent to ignore its priors does not reliably suppress them. PriorLock tests whether an agent can overcome this limitation with full CHANGELOG access.",
  },
  {
    id: "dated",
    title: "Dated Data: Tracing Knowledge Cutoffs in Large Language Models",
    authors: "Chern et al.",
    year: "2024",
    venue: "arXiv 2403.12958",
    url: "https://arxiv.org/abs/2403.12958",
    relevance:
      "Maps how training-data recency shapes model confidence, providing the theoretical grounding for why familiar-version bias exists and why G2 calibrates at 0.40.",
  },
  {
    id: "generalization",
    title: "Generalization vs. Memorization: Tracing Language Models' Capabilities Back to Pretraining Data",
    authors: "Li et al.",
    year: "2024",
    venue: "arXiv 2407.14985",
    url: "https://arxiv.org/abs/2407.14985",
    relevance:
      "Shows that memorization frequency in pretraining data is the primary driver of confident-but-wrong predictions — the same mechanism PriorLock exploits for synthetic library deviations.",
  },
];

const benefits = [
  {
    audience: "Researchers",
    color: "var(--accent)",
    bg: "rgba(91,156,255,0.07)",
    border: "rgba(91,156,255,0.22)",
    points: [
      "Isolates a single failure mode — prior-override — without task-difficulty confounds",
      "Model-free OOD proxy: the 0.40 familiar baseline holds across domains by construction, not empirical luck",
      "Provides a prior-override training signal for RLHF and fine-tuning experiments",
      "Reproducible: engine + cartridge architecture means any lab can replicate results identically",
      "Extensible: add any domain via one CLI command; CI enforces the 6-gate contract automatically",
    ],
  },
  {
    audience: "Practitioners",
    color: "var(--green)",
    bg: "rgba(62,207,142,0.07)",
    border: "rgba(62,207,142,0.25)",
    points: [
      "Identify prior-locked models before deploying them against evolving codebases or APIs",
      "Complement Terminal-Bench scores: TB measures terminal competence, PriorLock measures prior-override capability",
      "Select models by prior-override score for domains where library behavior changes frequently",
      "Use as a regression test when upgrading to a new model checkpoint",
      "Leaderboard gives an instant apples-to-apples comparison across frontier models",
    ],
  },
];

export default function Research() {
  return (
    <section id="research" className="section">
      {/* ── What is PriorLock ── */}
      <p className="section-label">About</p>
      <h2 className="section-title">
        What is <span>PriorLock</span>?
      </h2>
      <p className="section-lead">
        PriorLock is a Harbor-native reinforcement-learning environment that measures one thing precisely:
        can an AI agent override its memorized training-data priors when the live environment contradicts them?
      </p>

      <div className="mb-12 grid gap-4 sm:grid-cols-3">
        {[
          {
            icon: "⚙️",
            title: "The Problem",
            body:
              "Large language models memorize the APIs, libraries, and conventions they saw during training. When a task environment ships a newer, subtly different library, the model confidently applies its prior — producing wrong outputs that pass the visible smoke tests and never trigger an exception.",
          },
          {
            icon: "🔬",
            title: "The Measurement",
            body:
              "PriorLock ships a synthetic library in two forms: familiar (matches common training-data shapes) and installed (docs describe the live behaviour). The score gap between familiar and gold measures prior-lock strength. The familiar baseline is calibrated to 0.40 — model-free, domain-invariant.",
          },
          {
            icon: "📐",
            title: "The Signal",
            body:
              "A model that scores 0.40 is fully prior-locked — it cannot override memorized behavior even with access to a full CHANGELOG and API reference. A model that scores 1.0 reads the environment and applies it. The distance from 0.40 to 1.0 is the prior-override signal researchers and practitioners care about.",
          },
        ].map((c) => (
          <div key={c.title} className="card flex flex-col gap-3 p-6">
            <span className="text-2xl">{c.icon}</span>
            <p className="font-semibold tracking-tight">{c.title}</p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {c.body}
            </p>
          </div>
        ))}
      </div>

      {/* ── How it works ── */}
      <p className="section-label mt-16">Mechanics</p>
      <h2 className="section-title">
        How it <span>works</span>
      </h2>
      <p className="section-lead">
        PriorLock uses an engine + cartridge model. The engine is domain-blind — it handles
        Harbor scheduling, grading, CI, and the 6-gate offline validation protocol.
        A cartridge is a per-domain plug-in: a synthetic library plus a deviation spec.
      </p>

      <div className="mb-12 overflow-hidden rounded-[var(--radius)] border" style={{ borderColor: "var(--border)" }}>
        {[
          {
            step: "01",
            title: "Agent receives task",
            detail:
              "The Harbor container exposes an instruction.md (task description + I/O spec), a docs/ folder (CHANGELOG, API reference), and the installed synthetic library. No oracle. No answer key. Network disabled.",
          },
          {
            step: "02",
            title: "Agent writes a solution",
            detail:
              "The agent should read the CHANGELOG and API reference for the installed library, then write solve.py. A model with strong priors may skip the docs and apply familiar behaviour instead.",
          },
          {
            step: "03",
            title: "Visible tests run",
            detail:
              "Smoke tests run inside the container. Both the familiar path and the gold path can pass them — they are not a side channel for the answer. A prior-locked agent may see green and still score mid-rung.",
          },
          {
            step: "04",
            title: "Grader scores the output",
            detail:
              "The grader scores against environment ground truth. Prior-locked solutions land on the mid rung (0.40). Gold solutions reach 1.0. Exact scoring weights and probe recipes are not published.",
          },
          {
            step: "05",
            title: "Stage-0 validates the domain",
            detail:
              "Before any live agent run, 12 offline gates verify the task is well-formed: G1 gold=1.0, G2 familiar=0.40, G3 stub=0.0, G4 strict ladder, G5 visible tests pass both paths, G6 oracle files absent from the agent surface, G7 bypass=0.0, G8 tamper-proof, G9 every probe discriminates, G10 host verifier preserved, G11 shipped oracle scores 1.0, G12 canary never reaches the agent.",
          },
        ].map((r, i, arr) => (
          <div
            key={r.step}
            className="flex gap-5 p-5 sm:p-6"
            style={{
              background: i % 2 === 0 ? "var(--bg2)" : "var(--bg3)",
              borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : undefined,
            }}
          >
            <span
              className="font-mono text-xs font-bold flex-shrink-0 mt-0.5"
              style={{ color: "var(--accent)" }}
            >
              {r.step}
            </span>
            <div>
              <p className="font-semibold text-sm tracking-tight">{r.title}</p>
              <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                {r.detail}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Scope ── */}
      <p className="section-label mt-16">Scope</p>
      <h2 className="section-title">
        What PriorLock <span>covers</span>
      </h2>

      <div className="mb-12 grid gap-4 sm:grid-cols-2">
        <div
          className="rounded-[var(--radius)] border p-5"
          style={{ background: "rgba(62,207,142,0.07)", borderColor: "rgba(62,207,142,0.25)" }}
        >
          <p className="mb-3 font-mono text-xs font-bold uppercase tracking-widest" style={{ color: "var(--green)" }}>
            In scope
          </p>
          <ul className="space-y-2">
            {[
              "Any domain where a familiar API shape exists in pretraining data",
              "Installed behaviour that differs from what models typically memorize",
              "Synthetic libraries that can ship inside a Harbor container",
              "Domains validated by the Stage-0 offline contract",
            ].map((item) => (
              <li key={item} className="flex gap-2 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                <span style={{ color: "var(--green)", flexShrink: 0 }}>✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div
          className="rounded-[var(--radius)] border p-5"
          style={{ background: "rgba(240,113,120,0.07)", borderColor: "rgba(240,113,120,0.25)" }}
        >
          <p className="mb-3 font-mono text-xs font-bold uppercase tracking-widest" style={{ color: "var(--red)" }}>
            Out of scope
          </p>
          <ul className="space-y-2">
            {[
              "General coding ability (use Terminal-Bench for that)",
              "Novel APIs with no pretraining prior — prior-lock signal disappears",
              "Tasks where visible smoke tests already reveal the answer",
              "Real published libraries (training contamination invalidates G2)",
            ].map((item) => (
              <li key={item} className="flex gap-2 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                <span style={{ color: "var(--red)", flexShrink: 0 }}>✗</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* ── Benefits ── */}
      <p className="section-label mt-16">Impact</p>
      <h2 className="section-title">
        Who benefits and <span>how</span>
      </h2>

      <div className="mb-12 grid gap-4 sm:grid-cols-2">
        {benefits.map((b) => (
          <div
            key={b.audience}
            className="rounded-[var(--radius)] border p-5"
            style={{ background: b.bg, borderColor: b.border }}
          >
            <p
              className="mb-3 font-mono text-xs font-bold uppercase tracking-widest"
              style={{ color: b.color }}
            >
              {b.audience}
            </p>
            <ul className="space-y-2">
              {b.points.map((pt) => (
                <li key={pt} className="flex gap-2 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                  <span style={{ color: b.color, flexShrink: 0 }}>→</span>
                  {pt}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* ── References ── */}
      <p className="section-label mt-16">Literature</p>
      <h2 className="section-title">
        Research <span>foundations</span>
      </h2>
      <p className="section-lead">
        PriorLock operationalises findings from the following peer-reviewed and preprint works.
      </p>

      <div className="grid gap-3">
        {papers.map((p) => (
          <a
            key={p.id}
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            className="card group flex flex-col gap-2 p-5 transition-colors"
            style={{ textDecoration: "none" }}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <p className="text-sm font-semibold leading-snug tracking-tight group-hover:text-[var(--accent)] transition-colors">
                  {p.title}
                </p>
                <p className="mt-0.5 font-mono text-xs" style={{ color: "var(--muted)" }}>
                  {p.authors} · {p.year} · {p.venue}
                </p>
              </div>
              <span
                className="flex-shrink-0 font-mono text-xs mt-0.5 transition-colors group-hover:text-[var(--accent)]"
                style={{ color: "var(--muted)" }}
              >
                ↗
              </span>
            </div>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {p.relevance}
            </p>
          </a>
        ))}
      </div>
    </section>
  );
}
