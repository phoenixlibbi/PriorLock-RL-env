const domains = [
  { tag: "Python API", name: "coding", count: 17, status: "active" as const },
  { tag: "SQL Engine", name: "sql", count: 7, status: "active" as const },
  { tag: "Linux CLI", name: "linux", count: 7, status: "active" as const },
  { tag: "Config", name: "config", count: 4, status: "active" as const },
  { tag: "Cloud API", name: "cloud", count: 4, status: "active" as const },
  { tag: "Finance", name: "finance", count: 5, status: "active" as const },
  { tag: "Math", name: "math", count: 4, status: "active" as const },
  { tag: "Frontend", name: "frontend", count: 6, status: "active" as const },
  { tag: "Backend", name: "backend", count: 7, status: "active" as const },
  {
    tag: "Extend",
    name: "your domain",
    count: null as number | null,
    status: "soon" as const,
    dashed: true as boolean | undefined,
  },
];

export default function Domains() {
  return (
    <section id="domains" className="section">
      <p className="section-label">Cartridges</p>
      <h2 className="section-title">Domains</h2>
      <p className="section-lead">
        Each domain is a self-contained cartridge the engine can wrap into any Harbor
        task. Probe internals are not published — agents must read the docs shipped
        inside each task environment.
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {domains.map((d) => (
          <div
            key={d.name}
            className={`card flex h-full flex-col p-6 ${d.dashed ? "card-muted" : ""}`}
            style={{ borderStyle: d.dashed ? "dashed" : "solid" }}
          >
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span
                className="font-mono text-[11px] font-bold uppercase tracking-[0.12em]"
                style={{ color: "var(--accent)" }}
              >
                {d.tag}
              </span>
              <span className={`pill ${d.status === "active" ? "pill-active" : ""}`}>
                {d.status === "active" ? "Active" : "Soon"}
              </span>
            </div>

            <h3 className="mb-2 text-[15px] font-bold tracking-tight">{d.name}</h3>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {d.count != null
                ? `${d.count} probes · difficulty levels L1–L3 as applicable`
                : "Register via entry points or the cartridge generator"}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
