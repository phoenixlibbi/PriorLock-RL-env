const rows = [
  { model: "claude-opus-4", domain: "tablixdemo", score: null },
  { model: "claude-sonnet-4", domain: "tablixdemo", score: null },
  { model: "gpt-4o", domain: "tablixdemo", score: null },
];

export default function Leaderboard() {
  return (
    <section id="leaderboard" className="section">
      <p className="section-label">Results</p>
      <h2 className="section-title">Leaderboard</h2>
      <p className="section-lead">
        Prior-override rate across frontier models. Full calibration run in progress —
        results will populate here.
      </p>

      <div className="card overflow-hidden !p-0">
        <div className="overflow-x-auto">
          <table className="lb-table w-full min-w-[640px] text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["#", "Model", "Domain", "Score (pass@1)", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr
                  key={r.model}
                  style={{
                    borderBottom:
                      i < rows.length - 1 ? "1px solid var(--border)" : "none",
                  }}
                >
                  <td className="px-4 py-4 font-mono" style={{ color: "var(--muted)" }}>
                    —
                  </td>
                  <td className="px-4 py-4 font-semibold tracking-tight">{r.model}</td>
                  <td className="px-4 py-4" style={{ color: "var(--muted)" }}>
                    {r.domain}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <div className="score-track flex-1">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: "18%",
                            background:
                              "linear-gradient(90deg, transparent, rgba(91,156,255,0.35))",
                          }}
                        />
                      </div>
                      <span
                        className="w-6 text-right font-mono text-xs"
                        style={{ color: "var(--muted)" }}
                      >
                        —
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <span className="pill pill-pending">Pending run</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="mt-4 text-xs" style={{ color: "var(--muted)" }}>
        Expected range: frontier mean 0.40–0.75 · pass@1 25–60% · Wilson CI reported at n≥12
        per model.
      </p>
    </section>
  );
}
