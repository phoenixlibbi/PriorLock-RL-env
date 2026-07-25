import CodeBlock from "./CodeBlock";

export default function Hero() {
  return (
    <section className="relative px-6 sm:px-8 pt-20 sm:pt-28 pb-16 sm:pb-20">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-[420px] opacity-60"
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 50% 0%, rgba(91,156,255,0.16), transparent 70%)",
        }}
      />

      <div className="relative mx-auto flex max-w-3xl flex-col items-center text-center">
        <span className="badge rise mb-7">
          Domain-agnostic · RL environment · Measure &amp; train
        </span>

        <h1
          className="rise rise-delay-1 font-mono font-bold leading-[1.05] mb-4"
          style={{ fontSize: "clamp(2.75rem, 8vw, 4.75rem)", letterSpacing: "-0.04em" }}
        >
          Prior<span style={{ color: "var(--accent)" }}>Lock</span>
        </h1>

        <p
          className="rise rise-delay-1 mb-5 max-w-2xl text-sm sm:text-base font-medium leading-snug"
          style={{ color: "var(--text)" }}
        >
          A Domain-Agnostic Reinforcement Learning Environment for Measuring and
          Training Prior Override in Autonomous Agents
        </p>

        <p
          className="rise rise-delay-2 mb-4 max-w-xl text-base sm:text-lg leading-relaxed"
          style={{ color: "var(--muted)" }}
        >
          Wrap any Harbor task. Reward agents that override stale memorized priors
          when environment ground truth contradicts them — and train that skill
          with a real RL signal.
        </p>

        <p
          className="rise rise-delay-2 mb-8 font-mono text-xs sm:text-sm"
          style={{ color: "var(--muted)" }}
        >
          Created by{" "}
          <span style={{ color: "var(--text)" }}>Muhammad Labeeb Tariq</span>
          {" · "}
          <a
            href="mailto:labeebjutt80@gmail.com"
            className="transition-colors hover:text-[var(--text)]"
            style={{ color: "var(--accent)" }}
          >
            labeebjutt80@gmail.com
          </a>
        </p>

        <div
          className="rise rise-delay-2 mb-9 w-full max-w-lg rounded-[var(--radius)] border px-5 py-4 text-left"
          style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
        >
          <p
            className="mb-2 font-mono text-[10px] font-bold uppercase tracking-widest"
            style={{ color: "var(--muted)" }}
          >
            Wrap any Harbor task · you write nothing
          </p>
          <CodeBlock
            variant="inline"
            code="priorlock wrap tasks/my-task"
            preClassName="!border-0 !bg-transparent !px-0 !py-0 !text-sm !text-[var(--green)]"
          />
        </div>

        <div className="rise rise-delay-3 flex flex-wrap justify-center gap-3">
          <a href="#quickstart" className="btn btn-primary">
            Get started
          </a>
          <a
            href="https://github.com/phoenixlibbi/PriorLock-RL-env"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-ghost"
          >
            View on GitHub
          </a>
        </div>
      </div>
    </section>
  );
}
