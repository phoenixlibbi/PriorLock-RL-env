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

const vectors = [
  ["cat", "18 candidate oracle paths"],
  ["find", "8 needles + the _plx_* glob, whole filesystem"],
  ["import", "the verifier modules by name"],
  ["sys.path", "what the interpreter would resolve"],
  ["pip list", "the generated library as an installed dist"],
  ["walk", "filesystem walks from 6 bases"],
  ["env", "full os.environ, canary-grepped"],
  ["git", "log and show — history outlives a deleted file"],
  ["ps", "oracle process names in the process table"],
  ["canary", "grep the reachable filesystem for the planted string"],
  ["network", "egress attempts to 3 hosts — A7 as a fact"],
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

      {/* runtime isolation */}
      <p className="section-label mt-16">Isolation, not assertion</p>
      <h2 className="section-title">
        The runtime <span>leak probe</span>
      </h2>
      <p className="section-lead">
        A static check is not isolation. Grepping <code>environment/</code> answers a
        question about the repo; it says nothing about the container an agent actually
        gets. So the container gets asked directly.
      </p>

      <div className="mb-6 grid gap-4 lg:grid-cols-2">
        <div className="card p-6">
          <p className="mb-4 text-sm font-semibold tracking-tight">
            Every entrypoint an agent has
          </p>
          <table className="lb-table w-full">
            <thead>
              <tr>
                <th>Vector</th>
                <th>What it tries</th>
              </tr>
            </thead>
            <tbody>
              {vectors.map(([v, what]) => (
                <tr key={v}>
                  <td className="font-mono text-xs">{v}</td>
                  <td style={{ color: "var(--muted)" }}>{what}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col gap-4">
          <div
            className="rounded-[var(--radius)] border p-5"
            style={{ background: "rgba(91,156,255,0.07)", borderColor: "rgba(91,156,255,0.22)" }}
          >
            <p
              className="mb-2 font-mono text-xs font-bold uppercase tracking-widest"
              style={{ color: "var(--accent)" }}
            >
              A random canary, not a filename
            </p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              <code>wrap</code> plants <code>PLXCANARY-&lt;24 hex&gt;</code> into the
              grader and reference solutions — verifier-side files only. Asking
              &ldquo;is there a file called <code>gold.py</code>?&rdquo; cannot catch a
              copy under a different name or a fragment pasted into a layer. A random
              string can. Gate <strong>G12</strong> enforces it offline on every wrap;
              the probe greps the live container for the same string.
            </p>
          </div>

          <div
            className="rounded-[var(--radius)] border p-5"
            style={{ background: "rgba(230,180,74,0.07)", borderColor: "rgba(230,180,74,0.24)" }}
          >
            <p
              className="mb-2 font-mono text-xs font-bold uppercase tracking-widest"
              style={{ color: "var(--yellow)" }}
            >
              A probe that never fires proves nothing
            </p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
              Run against a deliberately leaky container, it flagged four vectors a
              clean one did not — <code>find probe_grade.py</code>,{" "}
              <code>find gold.py</code>, <code>find _plx_*</code> and the filesystem
              walk. The negative result is only worth reading because the positive one
              was checked first.
            </p>
          </div>

          <CodeBlock
            className="mt-auto"
            code={`priorlock leakprobe <task>
harbor run -p <task>__leakprobe -a oracle`}
          />
        </div>
      </div>

      <p className="mb-12 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
        The probe ships as a sibling Harbor task with an <code>environment/</code>{" "}
        copied from the original — same image, same mounts, same network posture.
        Probing a purpose-built image would prove nothing about the one agents run in.
        The trace below is from the deployed container, not a rehearsal.
      </p>

      <div className="card mb-12 p-6">
        <CodeBlock
          code={`leak probe: 49 attempts
  positive control: PASS — the agent's own library imports, so absences are meaningful
  oracle reachable from the agent: 0
  runner surface (judged by content, not existence):
    ok   /solution      contains only runner artefacts: probe.py, solve.sh
    ok   /logs          contains only runner artefacts: agent, verifier
    ok   /logs/verifier contains only runner artefacts: (empty)
    ok   /logs/agent    contains only runner artefacts: oracle.txt
  canary not on the agent surface
  network egress reachable: pypi.org:443, github.com:443, 1.1.1.1:53
    NOTE: the host task declares allow_internet = true — inherited
    posture, measured and reported, not a containment breach.

ISOLATION PROVEN AT RUNTIME                              reward 1.0`}
        />
        <p className="mt-4 text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
          <strong>The positive control is the line that matters.</strong> Every other
          result here is an absence, and an absence is only evidence if the instrument
          was working. On the first live run the control <em>failed</em> — the probe
          executes from <code>/tmp</code>, so the repo was off <code>sys.path</code> and
          all seven <code>ModuleNotFoundError</code>s meant nothing. A failed control now
          forces <code>INCONCLUSIVE</code>, which scores 0.0 exactly like a leak.
        </p>
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

    <probe>                      override         1.00
    <probe>                      override         1.00
    <probe>                      override         1.00

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
