const rows = [
  { model: "claude-opus-4",    domain: "tablixdemo", score: null },
  { model: "claude-sonnet-4",  domain: "tablixdemo", score: null },
  { model: "gpt-4o",           domain: "tablixdemo", score: null },
];

export default function Leaderboard() {
  return (
    <section id="leaderboard" className="py-18 px-8 max-w-5xl mx-auto">
      <h2 className="font-mono text-2xl font-bold mb-3">Leaderboard</h2>
      <p className="text-sm mb-8 max-w-xl" style={{ color: "var(--muted)" }}>
        Prior-override rate across frontier models. Full calibration run in progress —
        results will populate here.
      </p>

      <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--border)" }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: `1px solid var(--border)` }}>
              {["#", "Model", "Domain", "Score (pass@1)", "Status"].map((h) => (
                <th
                  key={h}
                  className="text-left px-4 py-2.5 font-mono text-xs tracking-widest uppercase"
                  style={{ color: "var(--muted)" }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={r.model}
                className="transition-colors"
                style={{ borderBottom: i < rows.length - 1 ? `1px solid var(--border)` : "none" }}
              >
                <td className="px-4 py-3.5 font-mono" style={{ color: "var(--muted)" }}>—</td>
                <td className="px-4 py-3.5 font-semibold">{r.model}</td>
                <td className="px-4 py-3.5" style={{ color: "var(--muted)" }}>{r.domain}</td>
                <td className="px-4 py-3.5">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--border)" }}>
                      <div className="h-full rounded-full" style={{ width: "0%", background: "var(--accent)" }} />
                    </div>
                    <span className="font-mono text-xs w-6 text-right" style={{ color: "var(--muted)" }}>—</span>
                  </div>
                </td>
                <td className="px-4 py-3.5">
                  <span
                    className="text-xs px-2 py-0.5 rounded border"
                    style={{
                      background: "var(--bg3)",
                      borderColor: "var(--border)",
                      color: "var(--muted)",
                    }}
                  >
                    pending run
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs" style={{ color: "var(--muted)" }}>
        Expected range: frontier mean 0.40–0.75 · pass@1 25–60% · Wilson CI reported at n≥12 per model.
      </p>
    </section>
  );
}
