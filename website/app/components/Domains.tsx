const domains = [
  {
    tag: "Python API",
    status: "active" as const,
    name: "coding",
    desc: "15 probes (L1–L3) across 5 categories: collection, encoding, numeric, sort, text. Includes 2 L3 workflow pipelines.",
    deviations: ["default_flip: 6 · value_remap: 4 · result_shape: 3", "L3: ETL pipeline, financial report"],
    dashed: false,
  },
  {
    tag: "SQL Engine",
    status: "active" as const,
    name: "sql",
    desc: "7 probes (L1–L3): NULL handling, JOIN semantics, GROUP BY, DISTINCT case folding. 2 L2 coupled + 1 L3 workflow.",
    deviations: ["L2: null handling + sort pairs", "L3: filter → join → aggregate pipeline"],
    dashed: false,
  },
  {
    tag: "Linux CLI",
    status: "active" as const,
    name: "linux",
    desc: "6 probes (L1–L3): find, grep, sort, chmod, symlinks. 1 L2 coupled + 1 L3 workflow probe.",
    deviations: ["L2: find + grep interaction", "L3: find → grep → sort pipeline"],
    dashed: false,
  },
  {
    tag: "Config Parser",
    status: "active" as const,
    name: "config",
    desc: "4 L1 probes: YAML merge keys, boolean parsing, anchor resolution, schema validation.",
    deviations: ["merge key precedence flipped", "yes/no boolean semantics changed"],
    dashed: false,
  },
  {
    tag: "Cloud API",
    status: "active" as const,
    name: "cloud",
    desc: "5 L1 probes: instance sizing, network ACLs, storage lifecycle, DNS TTL, load balancer draining.",
    deviations: ["default instance type changed", "ACL evaluation order flipped"],
    dashed: false,
  },
  {
    tag: "Finance",
    status: "active" as const,
    name: "finance",
    desc: "7 probes (L1–L2): currency conversion, tax brackets, compound interest, rounding modes. 2 L2 coupled probes.",
    deviations: ["L2: tax + compound interaction", "L2: currency + rounding interaction"],
    dashed: false,
  },
  {
    tag: "Math Library",
    status: "active" as const,
    name: "math",
    desc: "4 L1 probes: banker's rounding, matrix multiplication order, standard deviation (population vs sample), overflow handling.",
    deviations: ["rounding mode: half_up → half_even", "std default: sample → population"],
    dashed: false,
  },
  {
    tag: "Extend",
    status: "soon" as const,
    name: "Add your domain",
    desc: "Install via pip, register through entry points, or use the auto-cartridge generator. The engine handles everything else.",
    deviations: ["pip install priorlock-<domain>", "priorlock cartridge generate"],
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
