const stats = [
  { value: "0.40", label: "Prior-locked baseline score" },
  { value: "1.0",  label: "Gold (prior-aware) score" },
  { value: "2",    label: "Silent deviations per domain" },
  { value: "6",    label: "Stage-0 offline gates" },
];

export default function Stats() {
  return (
    <div
      className="flex justify-center border-t border-b divide-x"
      style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
    >
      {stats.map((s) => (
        <div key={s.label} className="flex-1 max-w-[220px] py-7 px-6 text-center"
          style={{ borderColor: "var(--border)" }}>
          <span className="font-mono text-3xl font-extrabold block mb-1"
            style={{ color: "var(--accent)" }}>
            {s.value}
          </span>
          <p className="text-xs" style={{ color: "var(--muted)" }}>{s.label}</p>
        </div>
      ))}
    </div>
  );
}
