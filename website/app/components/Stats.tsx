const stats = [
  { value: "0.40", label: "Prior-locked baseline — structural, not calibrated" },
  { value: "0/104", label: "False accepts · Wilson95 upper 0.036" },
  { value: "12", label: "Stage-0 offline gates" },
  { value: "0", label: "Lines a task author has to write" },
];

export default function Stats() {
  return (
    <div className="border-y" style={{ borderColor: "var(--border)", background: "rgba(14,19,26,0.72)" }}>
      <div
        className="mx-auto grid grid-cols-2 lg:grid-cols-4 divide-x divide-y lg:divide-y-0"
        style={{ maxWidth: "var(--max)", borderColor: "var(--border)" }}
      >
        {stats.map((s) => (
          <div
            key={s.label}
            className="px-5 py-8 text-center sm:px-6"
            style={{ borderColor: "var(--border)" }}
          >
            <span
              className="mb-2 block font-mono text-3xl font-bold tracking-tight sm:text-4xl"
              style={{ color: "var(--accent)" }}
            >
              {s.value}
            </span>
            <p className="text-xs leading-snug sm:text-[13px]" style={{ color: "var(--muted)" }}>
              {s.label}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
