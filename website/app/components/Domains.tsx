const domains = [
  {
    tag: "Python API",
    name: "coding",
    count: 17,
    blurb: "Synthetic library surfaces that look like everyday data APIs.",
    status: "active" as const,
  },
  {
    tag: "SQL Engine",
    name: "sql",
    count: 7,
    blurb: "Query-shaped interfaces where priors about dialect are strong.",
    status: "active" as const,
  },
  {
    tag: "Linux CLI",
    name: "linux",
    count: 7,
    blurb: "Command-line tools agents think they already know.",
    status: "active" as const,
  },
  {
    tag: "Config",
    name: "config",
    count: 4,
    blurb: "Config / schema surfaces with familiar defaults.",
    status: "active" as const,
  },
  {
    tag: "Cloud API",
    name: "cloud",
    count: 4,
    blurb: "Cloud-client shaped calls common in training data.",
    status: "active" as const,
  },
  {
    tag: "Finance",
    name: "finance",
    count: 5,
    blurb: "Numeric / ledger-style APIs with convention-heavy priors.",
    status: "active" as const,
  },
  {
    tag: "Math",
    name: "math",
    count: 4,
    blurb: "Numeric helpers where edge conventions differ.",
    status: "active" as const,
  },
  {
    tag: "Frontend",
    name: "frontend",
    count: 6,
    blurb: "UI / framework-shaped surfaces agents memorize early.",
    status: "active" as const,
  },
  {
    tag: "Backend",
    name: "backend",
    count: 7,
    blurb: "Server / framework patterns with sticky priors.",
    status: "active" as const,
  },
  {
    tag: "Fundamentals",
    name: "fundamentals",
    count: 10,
    blurb: "Universal concepts (indexing, slicing, truthiness, division) that even small models have strong priors about.",
    status: "active" as const,
  },
  {
    tag: "Extend",
    name: "your domain",
    count: null as number | null,
    blurb: "Register a cartridge when the catalog cannot express your surface.",
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
        Ten active cartridges plug into the same engine. We publish coverage and
        difficulty bands — not what each probe checks. Agents learn installed behaviour
        from the docs inside the task container.
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
            <p className="mb-3 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {d.blurb}
            </p>
            <p
              className="mt-auto font-mono text-[11px]"
              style={{ color: "var(--muted)" }}
            >
              {d.count != null
                ? `${d.count} probes · L1–L3 as applicable`
                : "entry points / generator"}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
