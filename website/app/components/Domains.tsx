const domains = [
  {
    tag: "data science · active",
    name: "tablixdemo",
    desc: "Sales reporting tasks using the synthetic tablix v1.4 data-aggregation library. All Stage-0 gates verified.",
    deviations: ["group_by null keys → \"__missing__\"", "top_n ties → all included"],
    dashed: false,
  },
  {
    tag: "library api · active",
    name: "priorlock-env (kestrel)",
    desc: "8-deviation library environment using the synthetic kestrel v3.2 API. Frontier-model calibration in progress.",
    deviations: ["8 silent behavioral deviations", "familiar score = 0.40 verified"],
    dashed: false,
  },
  {
    tag: "coming soon",
    name: "Add your domain",
    desc: "Implement a synthetic library with ≥2 silent deviations, write a deviation spec, and scaffold tasks with the generator.",
    deviations: ["CLI: any programming domain", "config-driven, Docker-isolated"],
    dashed: true,
  },
];

export default function Domains() {
  return (
    <section id="domains" className="py-18 px-8 max-w-5xl mx-auto">
      <h2 className="font-mono text-2xl font-bold mb-3">Domains</h2>
      <p className="text-sm mb-10 max-w-xl" style={{ color: "var(--muted)" }}>
        Each domain is a self-contained cartridge: synthetic library + deviation spec +
        task templates. Add domains without touching the engine.
      </p>

      <div className="grid sm:grid-cols-3 gap-4">
        {domains.map((d) => (
          <div
            key={d.name}
            className="rounded-xl p-6 border transition-colors"
            style={{
              background: "var(--bg2)",
              borderColor: "var(--border)",
              borderStyle: d.dashed ? "dashed" : "solid",
              opacity: d.dashed ? 0.6 : 1,
            }}
          >
            <p className="font-mono text-xs font-bold tracking-widest uppercase mb-2.5"
              style={{ color: "var(--accent)" }}>
              {d.tag}
            </p>
            <h3 className="font-bold text-sm mb-2">{d.name}</h3>
            <p className="text-xs leading-relaxed mb-4" style={{ color: "var(--muted)" }}>
              {d.desc}
            </p>
            <div
              className="rounded-md p-3 font-mono text-xs leading-7"
              style={{ background: "var(--bg3)", color: "var(--muted)" }}
            >
              {d.deviations.map((dv, i) => (
                <div key={i}>
                  <span style={{ color: "var(--yellow)" }}>{d.dashed ? "+" : "Δ"}</span>{" "}
                  {dv}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
