export default function Hero() {
  return (
    <section className="flex flex-col items-center text-center px-8 pt-24 pb-20 max-w-3xl mx-auto">
      <span
        className="inline-block font-mono text-xs tracking-widest uppercase rounded-full px-4 py-1 mb-7 border"
        style={{
          color: "var(--accent)",
          background: "rgba(88,166,255,0.1)",
          borderColor: "rgba(88,166,255,0.25)",
        }}
      >
        harbor-native · rl environment · v0.1.0
      </span>

      <h1 className="font-mono font-extrabold leading-tight mb-6"
        style={{ fontSize: "clamp(36px,6vw,64px)", letterSpacing: "-0.02em" }}>
        Prior<span style={{ color: "var(--accent)" }}>Lock</span>
      </h1>

      <p className="text-lg mb-10 max-w-xl leading-relaxed" style={{ color: "var(--muted)" }}>
        A benchmark that measures whether AI agents can override stale memorized
        knowledge when confronted with ground truth inside the environment.
      </p>

      <div className="flex gap-3 flex-wrap justify-center">
        <a
          href="#quickstart"
          className="px-5 py-2.5 rounded-lg font-semibold text-sm transition-opacity hover:opacity-85 hover:no-underline"
          style={{ background: "var(--accent)", color: "#0d1117" }}
        >
          Get started
        </a>
        <a
          href="https://github.com/phoenixlibbi/PriorLock-RL-env"
          target="_blank"
          rel="noopener noreferrer"
          className="px-5 py-2.5 rounded-lg font-semibold text-sm border transition-opacity hover:opacity-85 hover:no-underline"
          style={{
            background: "var(--bg2)",
            borderColor: "var(--border)",
            color: "var(--text)",
          }}
        >
          View on GitHub
        </a>
      </div>
    </section>
  );
}
