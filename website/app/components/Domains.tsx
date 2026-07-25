const domains = [
  {
    tag: "Data science",
    status: "active" as const,
    name: "tablixdemo",
    desc: "Sales reporting tasks using the synthetic tablix v1.4 data-aggregation library. All Stage-0 gates verified.",
    deviations: ['group_by null keys → "__missing__"', "top_n ties → all included"],
    dashed: false,
  },
  {
    tag: "Library API",
    status: "active" as const,
    name: "priorlock-env (kestrel)",
    desc: "8-deviation library environment using the synthetic kestrel v3.2 API. Frontier-model calibration in progress.",
    deviations: ["8 silent behavioral deviations", "familiar score = 0.40 verified"],
    dashed: false,
  },
  {
    tag: "Coming soon",
    status: "soon" as const,
    name: "Add your domain",
    desc: "Implement a synthetic library with ≥2 silent deviations, write a deviation spec, and scaffold tasks with the generator.",
    deviations: ["CLI: any programming domain", "config-driven, Docker-isolated"],
    dashed: true,
  },
];

export default function Domains() {
  return (
    <section id="domains" className="section">
      <p className="section-label">Cartridges</p>
      <h2 className="section-title">Domains</h2>
      <p className="section-lead">
        Each domain is a self-contained cartridge: synthetic library + deviation spec + task
        templates. Add domains without touching the engine.
      </p>

      <div className="grid gap-4 sm:grid-cols-3">
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
            <p className="mb-4 flex-1 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              {d.desc}
            </p>

            <div
              className="mt-auto rounded-[var(--radius-sm)] p-3 font-mono text-[11px] leading-6"
              style={{ background: "var(--bg3)", color: "var(--muted)" }}
            >
              {d.deviations.map((dv) => (
                <div key={dv} className="flex gap-2">
                  <span style={{ color: d.dashed ? "var(--accent)" : "var(--yellow)" }}>
                    {d.dashed ? "+" : "Δ"}
                  </span>
                  <span>{dv}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
