import CodeBlock from "./CodeBlock";

const cheats = [
  ["memorise the visible signal", "overfit_public", "caught", "0.0"],
  ["oracle-steal", "oracle_steal", "caught", "0.0"],
  ["read internals", "read_internals", "caught", "0.0"],
  ["tamper config", "tamper_input", "caught", "0.0"],
  ["edit tests / grader", "edit_grader", "caught", "0.0"],
  ["constant / shape forgery", "shape_forgery", "caught", "0.0"],
  ["timeout / resource abuse", "timeout_abuse", "killed", "0.0"],
  ["self-report forgery", "self_report", "caught", "0.0"],
];

const receipt = [
  { k: "trials", v: "104", note: "8 classes × 13 archetypes" },
  { k: "all executed", v: "104/104", note: "none excluded from the denominator" },
  { k: "false accepts", v: "0/104", note: "Wilson95 [0.0000, 0.0356]" },
  { k: "required", v: "< 0.05", note: "upper bound — PASS" },
  { k: "false rejects", v: "0/13", note: "Wilson95 [0.0000, 0.2281]" },
  { k: "worst surviving", v: "0.0", note: "against a 0.40 baseline" },
];

export default function Soundness() {
  return (
    <section id="soundness" className="section">
      <p className="section-label">Proven, not asserted</p>
      <h2 className="section-title">
        The soundness <span>receipt</span>
      </h2>
      <p className="section-lead">
        A verifier nobody attacked is untested, not sound. Eight cheat classes are
        thrown at every wrapped task, and the false-accept rate is reported with a
        95% Wilson interval — never a bare zero.
      </p>

      {/* the receipt */}
      <div
        className="mb-12 rounded-[var(--radius)] border p-6 sm:p-8"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >
        <div className="mb-5 flex flex-wrap items-baseline justify-between gap-3">
          <p
            className="font-mono text-xs font-bold uppercase tracking-widest"
            style={{ color: "var(--accent)" }}
          >
            Pooled receipt
          </p>
          <span
            className="rounded-full px-3 py-1 font-mono text-xs font-bold"
            style={{ background: "rgba(62,207,142,0.14)", color: "var(--green)" }}
          >
            SOUND
          </span>
        </div>

        <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
          {receipt.map((r) => (
            <div
              key={r.k}
              className="flex items-baseline justify-between gap-3 border-b pb-2"
              style={{ borderColor: "var(--border)" }}
            >
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                {r.k}
              </span>
              <span className="text-right">
                <span
                  className="font-mono text-sm font-bold"
                  style={{ color: r.k === "false accepts" ? "var(--green)" : "var(--text)" }}
                >
                  {r.v}
                </span>
                <span
                  className="ml-2 font-mono text-[10px]"
                  style={{ color: "var(--muted)" }}
                >
                  {r.note}
                </span>
              </span>
            </div>
          ))}
        </div>

        <p className="mt-5 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
          One task alone gives n=8 → Wilson upper <strong>0.324</strong>. Reporting
          that as &ldquo;zero false accepts&rdquo; would be exactly the bare-0% the
          standard forbids, so <code>--suite</code> pools across all 13 archetypes to
          earn the interval.
        </p>
      </div>

      {/* the classes */}
      <div className="mb-12 grid gap-4 lg:grid-cols-2">
        <div className="card p-6">
          <p className="mb-4 text-sm font-semibold tracking-tight">Eight cheat classes</p>
          <table className="lb-table w-full">
            <thead>
              <tr>
                <th>Class</th>
                <th>Result</th>
                <th style={{ textAlign: "right" }}>Score</th>
              </tr>
            </thead>
            <tbody>
              {cheats.map(([cls, id, result, score]) => (
                <tr key={id}>
                  <td>
                    {cls}
                    <span
                      className="ml-2 font-mono text-[10px]"
                      style={{ color: "var(--muted)" }}
                    >
                      {id}
                    </span>
                  </td>
                  <td style={{ color: "var(--green)" }}>{result}</td>
                  <td className="font-mono" style={{ textAlign: "right" }}>
                    {score}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col gap-4">
          <div
            className="rounded-[var(--radius)] border p-5"
            style={{ background: "rgba(230,180,74,0.07)", borderColor: "rgba(230,180,74,0.24)" }}
          >
            <p
              className="mb-2 font-mono text-xs font-bold uppercase tracking-widest"
              style={{ color: "var(--yellow)" }}
            >
              A cheat that never ran is not a caught cheat
            </p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              Every cheat writes an execution marker as its first act. One that scores
              0 <em>without</em> its marker is reported <code>not_executed</code> and
              excluded from the denominator — otherwise the statistic is inflated by
              cheats that silently no-op&apos;d.
            </p>
          </div>

          <div
            className="rounded-[var(--radius)] border p-5"
            style={{ background: "rgba(91,156,255,0.07)", borderColor: "rgba(91,156,255,0.22)" }}
          >
            <p
              className="mb-2 font-mono text-xs font-bold uppercase tracking-widest"
              style={{ color: "var(--accent)" }}
            >
              False accept means above 0.40, not above zero
            </p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              Scoring 0.40 by naively calling the library is the measurement working,
              not a cheat surviving. A false accept is credit bought without doing the
              work.
            </p>
          </div>

          <CodeBlock
            className="mt-auto"
            code={`priorlock cheats <task>
priorlock cheats <task> --suite -o receipt.json`}
          />
        </div>
      </div>

      {/* verified end to end */}
      <p className="section-label mt-16">Verified end to end</p>
      <h2 className="section-title">
        On a real <span>hard task</span>
      </h2>
      <p className="section-lead">
        A 12-module ML debugging task with a 5-part runbook, 19 verifier tests and a
        27 KB oracle — taken byte-identical from a production Harbor 2.0 submission
        and converted with one command.
      </p>

      <div className="card p-6">
        <CodeBlock
          code={`=== Doctor · pipeline-drift-calibration-hard ===

  baseline task_score  1.0000   (oracle, before wrapping)
  observed task_score  1.0000   (oracle, after wrapping)
  drift                0.0000
  gap_score            1.0000   (prior-override, new signal)

    merge_precedence_remap       override         1.00
    tie_inclusive_topk           override         1.00
    range_end_inclusive          override         1.00

HEALTHY
  task_score is unchanged — wrapping did not perturb the host task`}
        />
        <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
          <strong>drift 0.0000</strong> is the number that matters: the task&apos;s own
          19-test verifier produced exactly the same 1.0 before and after conversion,
          and the probes contributed an independent score on top. Two facts about one
          run, neither contaminating the other.
        </p>
      </div>
    </section>
  );
}
