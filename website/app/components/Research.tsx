import CodeBlock from "./CodeBlock";

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
      "Shows that memorization frequency in pretraining data drives confident-but-wrong predictions — the class of failure PriorLock turns into a clean training and eval signal.",
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
      "Provides a prior-override training signal for RLHF, offline RL, and fine-tuning experiments",
      "Reproducible: engine + cartridge architecture means any lab can replicate results identically",
      "Extensible: add a domain via cartridge; CI enforces the Stage-0 gate contract automatically",
    ],
  },
  {
    audience: "Practitioners",
    color: "var(--green)",
    bg: "rgba(62,207,142,0.07)",
    border: "rgba(62,207,142,0.25)",
    points: [
      "Identify prior-locked models before deploying them against evolving codebases or APIs",
      "Complement Terminal-Bench: TB measures terminal competence; PriorLock measures prior-override",
      "Select models by prior-override score where library behaviour changes frequently",
      "Use as a regression test when upgrading to a new model checkpoint",
      "Leaderboard gives an apples-to-apples comparison across frontier models",
    ],
  },
];

const archLayers = [
  {
    title: "Harbor runner",
    body: "Schedules containers, collects reward.json, unchanged by wrapping. PriorLock is a guest in the Harbor lifecycle — not a fork of it.",
  },
  {
    title: "PriorLock engine",
    body: "Domain-blind: wrap, Stage-0 gates, composite scoring, cheat suite, leakprobe, calibration. Same machinery for every cartridge.",
  },
  {
    title: "Cartridges",
    body: "Per-domain plug-ins that supply a synthetic library surface and probe catalog. Authors pick a domain; they do not hand-author traps.",
  },
  {
    title: "Task docs (ground truth)",
    body: "CHANGELOG + API reference live inside the container. That is the only place agents — and the public — should learn installed behaviour.",
  },
];

export default function Research() {
  return (
    <section id="research" className="section">
      <p className="section-label">About</p>
      <h2 className="section-title">
        What is <span>PriorLock</span>?
      </h2>
      <p className="section-lead">
        PriorLock is a Harbor-native reinforcement-learning environment that measures one thing
        precisely: can an AI agent override its memorized training-data priors when the live
        environment contradicts them?
      </p>

      <div className="mb-12 grid gap-4 sm:grid-cols-3">
        {[
          {
            icon: "⚙️",
            title: "The Problem",
            body:
              "Models memorize APIs and conventions from pretraining. When a task ships a subtly different installed library, they confidently apply the prior — wrong outputs that still pass visible smoke tests and never throw.",
          },
          {
            icon: "🔬",
            title: "The Measurement",
            body:
              "Each wrapped task exposes a synthetic library plus docs for the installed behaviour. The score gap between a familiar (prior-shaped) solution and gold is the prior-lock strength. The mid rung is fixed at 0.40 by construction.",
          },
          {
            icon: "📐",
            title: "The Signal",
            body:
              "0.40 = fully prior-locked even with CHANGELOG access. 1.0 = read the environment and applied it. That distance is the prior-override signal for evaluation and RL.",
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

      {/* Architecture */}
      <p className="section-label mt-16">System</p>
      <h2 className="section-title">
        Engine + cartridge <span>architecture</span>
      </h2>
      <p className="section-lead">
        The brilliance is in the harness contract — dual scores, offline gates, isolation proofs —
        not in publishing which traps sit in the private catalog.
      </p>

      <div className="mb-12 grid gap-3 sm:grid-cols-2">
        {archLayers.map((layer, i) => (
          <div
            key={layer.title}
            className="rounded-[var(--radius)] border p-5"
            style={{
              background: i % 2 === 0 ? "var(--bg2)" : "var(--bg3)",
              borderColor: "var(--border)",
            }}
          >
            <p
              className="mb-2 font-mono text-[11px] font-bold uppercase tracking-widest"
              style={{ color: "var(--accent)" }}
            >
              {String(i + 1).padStart(2, "0")} · {layer.title}
            </p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {layer.body}
            </p>
          </div>
        ))}
      </div>

      <div
        className="mb-12 rounded-[var(--radius)] border p-5 sm:p-6"
        style={{ background: "rgba(91,156,255,0.06)", borderColor: "rgba(91,156,255,0.22)" }}
      >
        <p className="mb-3 text-sm font-semibold tracking-tight">Two scores, one run</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="font-mono text-xs font-bold" style={{ color: "var(--accent)" }}>
              task_score
            </p>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              The host Harbor verifier — untouched. Wrapping must not change whether the original
              task is solved (drift ≈ 0).
            </p>
          </div>
          <div>
            <p className="font-mono text-xs font-bold" style={{ color: "var(--accent)" }}>
              gap_score
            </p>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              Prior-override capability from injected probes. Independent of task difficulty — that
              is what Terminal-Bench cannot separate.
            </p>
          </div>
        </div>
      </div>

      {/* Pedagogical toy — NOT live catalog */}
      <p className="section-label mt-16">Pedagogy</p>
      <h2 className="section-title">
        How the idea <span>feels</span>
      </h2>
      <p className="section-lead">
        A clearly fictional illustration — not a live probe, not in the production catalog.
        Real tasks use different APIs and rotate selection so this example cannot be farmed.
      </p>

      <div
        className="mb-4 rounded-[var(--radius)] border px-4 py-3 font-mono text-[11px] font-bold uppercase tracking-widest"
        style={{
          background: "rgba(230,180,74,0.1)",
          borderColor: "rgba(230,180,74,0.35)",
          color: "var(--yellow)",
        }}
      >
        Illustrative only · not a production probe · do not treat as exam content
      </div>

      <div className="card mb-8 p-6">
        <CodeBlock
          code={`# Toy library "widgetlib" (fictional)
# CHANGELOG (installed): sort() now defaults nulls="last"
# Training-shaped prior: most models assume nulls="first"

# Prior-locked solution — skips docs, omits the kwarg
widgetlib.sort(rows)          # → mid rung 0.40

# Override solution — reads CHANGELOG, matches installed truth
widgetlib.sort(rows, nulls="last")   # → 1.0`}
        />
        <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
          Visible smoke tests only check shape (list in, list out). Both snippets can look
          &ldquo;green.&rdquo; The grader measures whether behaviour matches the{" "}
          <em>installed</em> docs — that is the prior-override signal.
        </p>
      </div>

      <div className="mb-12 grid gap-4 lg:grid-cols-2">
        <div className="card p-6">
          <p className="mb-3 text-sm font-semibold tracking-tight">Redacted agent trace · prior-locked</p>
          <CodeBlock
            code={`[agent] reads instruction.md
[agent] writes solve.py from memory
[tests] visible smoke … PASS
[grade] gap_score 0.40  prior_locked
        trusted familiar semantics over docs`}
          />
        </div>
        <div className="card p-6">
          <p className="mb-3 text-sm font-semibold tracking-tight">Redacted agent trace · override</p>
          <CodeBlock
            code={`[agent] opens docs/CHANGELOG.md
[agent] updates call sites to installed API
[tests] visible smoke … PASS
[grade] gap_score 1.00  override
        environment ground truth applied`}
          />
        </div>
      </div>

      {/* How it works */}
      <p className="section-label mt-16">Mechanics</p>
      <h2 className="section-title">
        How it <span>works</span>
      </h2>
      <p className="section-lead">
        End-to-end lifecycle for every wrapped Harbor task. Probe IDs and recipes stay
        task-local so public write-ups cannot become a cheat sheet.
      </p>

      <div
        className="mb-12 overflow-hidden rounded-[var(--radius)] border"
        style={{ borderColor: "var(--border)" }}
      >
        {[
          {
            step: "01",
            title: "Agent receives task",
            detail:
              "Container exposes instruction.md, docs/ (CHANGELOG + API reference), and the installed synthetic library. No oracle. No answer key. Network posture inherited from the host task.",
          },
          {
            step: "02",
            title: "Agent writes a solution",
            detail:
              "Success means reading the shipped docs and matching installed behaviour. Strong priors often skip the docs and re-apply familiar semantics instead.",
          },
          {
            step: "03",
            title: "Visible tests run",
            detail:
              "Smoke tests are deliberately non-discriminating: familiar and gold paths can both pass. Green tests are not a side channel for the answer.",
          },
          {
            step: "04",
            title: "Composite grader",
            detail:
              "Emits task_score (host verifier) and gap_score (prior-override). Mid rung 0.40 vs gold 1.0 is structural. Exact per-probe weights stay unpublished.",
          },
          {
            step: "05",
            title: "Stage-0 offline contract",
            detail:
              "Twelve gates must pass before any live agent run: gold / familiar / stub ladder, non-discriminating visibles, bypass & tamper resistance, discrimination, host preservation, oracle & canary hygiene — no Docker required for the gate suite.",
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
              className="mt-0.5 flex-shrink-0 font-mono text-xs font-bold"
              style={{ color: "var(--accent)" }}
            >
              {r.step}
            </span>
            <div>
              <p className="text-sm font-semibold tracking-tight">{r.title}</p>
              <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
                {r.detail}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Publish vs withhold */}
      <div
        className="mb-12 rounded-[var(--radius)] border p-5 sm:p-6"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >
        <p className="mb-4 text-sm font-semibold tracking-tight">What we publish vs withhold</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p
              className="mb-2 font-mono text-[11px] font-bold uppercase tracking-widest"
              style={{ color: "var(--green)" }}
            >
              Public
            </p>
            <ul className="space-y-1.5 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              <li>· Failure mode, ladder, dual scores</li>
              <li>· Engine / cartridge architecture</li>
              <li>· Gate contracts & soundness receipts</li>
              <li>· Domain coverage counts (not mechanisms)</li>
              <li>· Pedagogical toys labeled as non-live</li>
            </ul>
          </div>
          <div>
            <p
              className="mb-2 font-mono text-[11px] font-bold uppercase tracking-widest"
              style={{ color: "var(--red)" }}
            >
              Private
            </p>
            <ul className="space-y-1.5 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              <li>· Live probe IDs & argument recipes</li>
              <li>· Per-domain deviation lists</li>
              <li>· Exact grading weight formulas</li>
              <li>· Available to labs on request</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Scope */}
      <p className="section-label mt-16">Scope</p>
      <h2 className="section-title">
        What PriorLock <span>covers</span>
      </h2>

      <div className="mb-12 grid gap-4 sm:grid-cols-2">
        <div
          className="rounded-[var(--radius)] border p-5"
          style={{ background: "rgba(62,207,142,0.07)", borderColor: "rgba(62,207,142,0.25)" }}
        >
          <p
            className="mb-3 font-mono text-xs font-bold uppercase tracking-widest"
            style={{ color: "var(--green)" }}
          >
            In scope
          </p>
          <ul className="space-y-2">
            {[
              "Domains where a familiar API shape exists in pretraining data",
              "Installed behaviour that can diverge from memorized defaults",
              "Synthetic libraries shippable inside a Harbor container",
              "Tasks validated by the Stage-0 offline contract",
              "RL / eval loops that need a clean prior-override reward",
            ].map((item) => (
              <li
                key={item}
                className="flex gap-2 text-xs leading-relaxed"
                style={{ color: "var(--muted)" }}
              >
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
          <p
            className="mb-3 font-mono text-xs font-bold uppercase tracking-widest"
            style={{ color: "var(--red)" }}
          >
            Out of scope
          </p>
          <ul className="space-y-2">
            {[
              "General coding ability (use Terminal-Bench for that)",
              "Novel APIs with no pretraining prior — signal disappears",
              "Tasks where visible smoke tests already reveal the answer",
              "Real published libraries (contamination invalidates G2)",
            ].map((item) => (
              <li
                key={item}
                className="flex gap-2 text-xs leading-relaxed"
                style={{ color: "var(--muted)" }}
              >
                <span style={{ color: "var(--red)", flexShrink: 0 }}>✗</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Benefits */}
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
                <li
                  key={pt}
                  className="flex gap-2 text-xs leading-relaxed"
                  style={{ color: "var(--muted)" }}
                >
                  <span style={{ color: b.color, flexShrink: 0 }}>→</span>
                  {pt}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* References */}
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
                <p className="text-sm font-semibold leading-snug tracking-tight transition-colors group-hover:text-[var(--accent)]">
                  {p.title}
                </p>
                <p className="mt-0.5 font-mono text-xs" style={{ color: "var(--muted)" }}>
                  {p.authors} · {p.year} · {p.venue}
                </p>
              </div>
              <span
                className="mt-0.5 flex-shrink-0 font-mono text-xs transition-colors group-hover:text-[var(--accent)]"
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
