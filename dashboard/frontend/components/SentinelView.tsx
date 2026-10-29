"use client";

import dynamic from "next/dynamic";
import { Fragment, useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";
import type { AgentScan, Check, ScanReport } from "@/lib/sentinel";
import { STATE_COLOR } from "@/lib/status";
import type { Packet } from "./SentinelDome";

const SentinelDome = dynamic(() => import("./SentinelDome"), { ssr: false });

export type GateAgent = { id: string; name: string; trust: number | null; tools: string[]; approvals: string[] };
type Policy = {
  version: number;
  bannedPrimitives: string[];
  secretPatterns: string[];
  adviceTerms: string[];
  trustNeedsEvidenceFrom: number;
  executionKinds: string[];
};
type Decision = { decision: "allow" | "hold" | "deny"; reason: string };

const CHECKS = ["manifest", "trust", "execution", "secrets", "registry", "deviation", "contracts"] as const;
const FILE_SCANS = new Set(["execution", "secrets", "deviation"]);
const UNDECLARED = "undeclared.tool";

// A PASS that looked at nothing is not evidence. Surface it instead of letting it read as "safe".
function passKind(c: Check): "exempt" | "vacuous" | null {
  if (c.verdict !== "PASS" || !FILE_SCANS.has(c.check)) return null;
  if (/not asserted/i.test(c.summary)) return "exempt";
  return c.scanned === 0 ? "vacuous" : null;
}

function Mark({ state, label }: { state: string; label?: string }) {
  const d =
    state === "PASS" || state === "allow"
      ? "M3 8.5 6.5 12 13 4.5"
      : state === "FAIL" || state === "deny"
        ? "M4 4l8 8M12 4l-8 8"
        : "M8 3v6M8 12v.5";
  return (
    <span className="inline-flex items-center gap-1.5" style={{ color: STATE_COLOR[state] }}>
      <svg viewBox="0 0 16 16" className="size-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d={d} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="text-ink">{label ?? state}</span>
    </span>
  );
}

export function SentinelView({
  agents,
  policy,
  initialScan,
}: {
  agents: GateAgent[];
  policy: Policy;
  initialScan: ScanReport | null;
}) {
  const still = !!useReducedMotion();
  const [scan, setScan] = useState<ScanReport | null>(initialScan);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  const [agentId, setAgentId] = useState(agents[0]?.id ?? "");
  const agent = agents.find((a) => a.id === agentId)!;
  const toolOptions = [...new Set([...agent.tools, ...agent.approvals, UNDECLARED])];
  const [tool, setTool] = useState(toolOptions[0]);
  const [kind, setKind] = useState("read");
  const [asking, setAsking] = useState(false);
  const [result, setResult] = useState<(Decision & { agent: string; tool: string; kind: string }) | null>(null);
  const [gateError, setGateError] = useState<string | null>(null);
  const [history, setHistory] = useState<(Decision & { agent: string; tool: string; kind: string })[]>([]);
  const [packet, setPacket] = useState<Packet | null>(null);

  const runScan = async () => {
    setScanning(true);
    setScanError(null);
    try {
      const res = await fetch("/sentinel/scan", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setScan(data);
    } catch (e) {
      setScanError((e as Error).message || "Scan failed — is Python available on the server?");
    } finally {
      setScanning(false);
    }
  };

  // Only the first visit in a server session needs an automatic scan.
  useEffect(() => {
    if (!initialScan) runScan();
  }, []);

  const pickAgent = (id: string) => {
    const next = agents.find((a) => a.id === id);
    if (!next) return;
    setAgentId(id);
    setTool([...next.tools, ...next.approvals, UNDECLARED][0]);
  };

  const ask = async () => {
    setAsking(true);
    setGateError(null);
    try {
      const res = await fetch("/sentinel/gate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ agent: agentId, tool, kind }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      const entry = { ...data, agent: agentId, tool, kind };
      setResult(entry);
      setHistory((h) => [entry, ...h].slice(0, 6));
      setPacket({ nonce: Date.now(), agent: agentId, decision: data.decision });
    } catch (e) {
      setGateError((e as Error).message);
    } finally {
      setAsking(false);
    }
  };

  const verdictOf = (id: string) => scan?.agents.find((a) => a.id === id)?.verdict ?? null;
  const trustOf = (a: GateAgent) => scan?.agents.find((s) => s.id === a.id)?.effective_trust ?? a.trust ?? 0;
  const counts = scan
    ? scan.agents.flatMap((a) => a.checks).reduce(
        (c, ch) => {
          const k = passKind(ch);
          if (k) c[k]++;
          return c;
        },
        { exempt: 0, vacuous: 0 },
      )
    : null;

  return (
    <>
      {/* Status strip */}
      <dl className="mt-10 grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-bg p-4">
          <dt className="text-[11px] text-mute">Fleet verdict</dt>
          <dd className="mt-1 text-sm">
            {scan ? <Mark state={scan.verdict} /> : <span className="text-mute">{scanning ? "scanning…" : "not scanned"}</span>}
          </dd>
        </div>
        <div className="bg-bg p-4">
          <dt className="text-[11px] text-mute">Execution boundary</dt>
          <dd className="mt-1 text-sm">
            <Mark state="deny" label="Deny by default" />
            <span className="mt-1 block text-[11px] text-mute">{policy.executionKinds.join(" · ")}</span>
          </dd>
        </div>
        <div className="bg-bg p-4">
          <dt className="text-[11px] text-mute">Approval queue</dt>
          <dd className="mt-1 text-sm text-soft">Not built yet — see below</dd>
        </div>
        <div className="bg-bg p-4">
          <dt className="text-[11px] text-mute">Policy</dt>
          <dd className="mt-1 text-sm text-soft">
            v{policy.version} · <code className="font-pixel text-[10px]">security/policies/sentinel.yaml</code>
          </dd>
        </div>
      </dl>

      {/* Dome + gate simulator */}
      <section className="mt-10 grid gap-4 lg:grid-cols-[1.35fr_1fr]" aria-label="Runtime gate">
        <div className="frame relative h-[420px] overflow-hidden bg-panel/40 sm:h-[480px]">
          <SentinelDome
            agents={agents.map((a) => ({ id: a.id, verdict: verdictOf(a.id), trust: trustOf(a) }))}
            selected={agentId}
            packet={packet}
            onPick={pickAgent}
            still={still}
          />
          <div className="pointer-events-none absolute top-4 left-5">
            <p className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">The shell is the gate</p>
            <ul className="mt-2 space-y-1 text-[11px] text-mute">
              <li>cube colour = last scan verdict</li>
              <li>
                <span style={{ color: STATE_COLOR.allow }}>allow</span> crosses ·{" "}
                <span style={{ color: STATE_COLOR.hold }}>hold</span> waits on the shell ·{" "}
                <span style={{ color: STATE_COLOR.deny }}>deny</span> falls back
              </li>
            </ul>
          </div>
        </div>

        <div className="frame p-5">
          <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Ask the gate</h2>
          <p className="mt-2 text-xs leading-relaxed text-mute">
            Sends a hypothetical action to the real runtime gate (
            <code className="font-pixel text-[10px]">security/sentinel/gate.py</code>). Nothing is executed — the gate only
            decides.
          </p>
          <div className="mt-5 grid gap-3">
            <label className="grid gap-1 text-[11px] text-mute">
              Agent
              <select value={agentId} onChange={(e) => pickAgent(e.target.value)} className="border border-line bg-panel px-3 py-2 text-sm text-ink">
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.id} · {a.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-[11px] text-mute">
              Tool
              <select value={tool} onChange={(e) => setTool(e.target.value)} className="border border-line bg-panel px-3 py-2 text-sm text-ink">
                {toolOptions.map((t) => (
                  <option key={t} value={t}>
                    {t === UNDECLARED
                      ? "a tool the manifest does not declare"
                      : `${t}${agent.approvals.includes(t) ? " (needs approval)" : ""}`}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-[11px] text-mute">
              Action kind
              <select value={kind} onChange={(e) => setKind(e.target.value)} className="border border-line bg-panel px-3 py-2 text-sm text-ink">
                <option value="read">read</option>
                <option value="write">write</option>
                <optgroup label="execution boundary">
                  {policy.executionKinds.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </optgroup>
              </select>
            </label>
            <button
              type="button"
              onClick={ask}
              disabled={asking}
              className="mt-1 bg-accent px-4 py-2.5 text-sm font-medium text-bg transition hover:bg-accent-hi disabled:opacity-60"
            >
              {asking ? "Asking the gate…" : "Send through the gate"}
            </button>
          </div>

          <div aria-live="polite" className="mt-5 min-h-16">
            {gateError && <p className="text-xs text-critical">{gateError}</p>}
            {result && !gateError && (
              <div className="border-t border-line pt-4">
                <p className="text-lg">
                  <Mark state={result.decision} label={result.decision.toUpperCase()} />
                </p>
                <p className="mt-1 text-xs text-soft">{result.reason}</p>
                <p className="mt-1 text-[11px] text-mute">
                  {result.agent} · {result.tool === UNDECLARED ? "undeclared tool" : result.tool} · {result.kind}
                </p>
              </div>
            )}
          </div>
          {history.length > 1 && (
            <ul className="mt-4 space-y-1 border-t border-line pt-3 text-[11px] text-mute">
              {history.slice(1).map((h, i) => (
                <li key={i} className="flex justify-between gap-3">
                  <span className="truncate">
                    {h.agent} · {h.tool === UNDECLARED ? "undeclared" : h.tool} · {h.kind}
                  </span>
                  <span style={{ color: STATE_COLOR[h.decision] }}>{h.decision}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* Conformance scan */}
      <section className="mt-16" aria-label="Conformance scan">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-medium text-ink">Conformance scan</h2>
            <p className="mt-1 text-xs text-mute">
              {scan
                ? `Sentinel ${scan.sentinel_version} · ran at ${scan.generated_at.slice(11, 16)} UTC · took ${(scan.durationMs / 1000).toFixed(1)} s · ${scan.agents.length} registered agents × ${CHECKS.length} checks`
                : scanning
                  ? "Scanning every registered agent — this can take up to a minute…"
                  : "No scan in this server session yet."}
            </p>
          </div>
          <button
            type="button"
            onClick={runScan}
            disabled={scanning}
            className="frame px-4 py-2 text-sm text-ink hover:border-line-strong disabled:opacity-60"
          >
            {scanning ? "Scanning…" : scan ? "Run scan again" : "Run scan"}
          </button>
        </div>
        {scanError && <p className="mt-3 text-xs text-critical">{scanError}</p>}

        {counts && (counts.exempt > 0 || counts.vacuous > 0) && (
          <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-soft">
            <svg viewBox="0 0 16 16" className="mt-px size-3.5 shrink-0 text-warning" fill="currentColor" aria-label="Warning">
              <path d="M8 1.5 15 14H1L8 1.5Zm-.75 5v4h1.5v-4h-1.5Zm0 5v1.5h1.5V11.5h-1.5Z" />
            </svg>
            <span>
              {counts.exempt > 0 && `${counts.exempt} PASS ${counts.exempt === 1 ? "is" : "are"} an exemption (execution-enabled agent — its order path is not scanned). `}
              {counts.vacuous > 0 && `${counts.vacuous} PASS looked at 0 files. `}
              A PASS on nothing is not evidence — these are marked ∅.
            </span>
          </p>
        )}

        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-[11px] text-mute">
              <tr>
                <th className="py-2 pr-3 font-normal">Agent</th>
                <th className="py-2 pr-3 font-normal">Verdict</th>
                <th className="py-2 pr-3 font-normal">Trust</th>
                {CHECKS.map((c) => (
                  <th key={c} className="py-2 pr-3 font-normal capitalize">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(scan?.agents ?? []).map((a) => (
                <Fragment key={a.id}>
                  <tr
                    onClick={() => setOpen((o) => (o === a.id ? null : a.id))}
                    className={`cursor-pointer border-t border-line transition-colors hover:bg-white/[0.03] ${open === a.id ? "bg-white/[0.03]" : ""}`}
                    aria-expanded={open === a.id}
                  >
                    <td className="py-3 pr-3 font-pixel text-xs text-accent-hi">{a.id}</td>
                    <td className="py-3 pr-3">
                      <Mark state={a.verdict} />
                    </td>
                    <td className="py-3 pr-3 text-soft tabular-nums">{a.effective_trust}</td>
                    {CHECKS.map((name) => {
                      const c = a.checks.find((x) => x.check === name);
                      if (!c) return <td key={name} className="py-3 pr-3 text-mute">—</td>;
                      const k = passKind(c);
                      return (
                        <td key={name} className="py-3 pr-3" title={c.summary}>
                          {k ? (
                            <span className="inline-flex items-center gap-1.5 text-mute">
                              <span className="font-pixel text-[11px] text-warning">∅</span>
                              {k === "exempt" ? "exempt" : "0 files"}
                            </span>
                          ) : (
                            <Mark state={c.verdict} />
                          )}
                        </td>
                      );
                    })}
                  </tr>
                  {open === a.id && <ScanDetail a={a} />}
                </Fragment>
              ))}
            </tbody>
          </table>
          {!scan && (
            <p className="frame mt-2 p-6 text-center text-sm text-mute">
              {scanning ? "Running python -m security.sentinel scan…" : "Run a scan to see each agent's checks."}
            </p>
          )}
        </div>
      </section>

      {/* Policy + trust */}
      <section className="mt-16 grid gap-4 md:grid-cols-3" aria-label="Policy">
        <div className="frame p-5">
          <h3 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Banned execution primitives</h3>
          <p className="mt-2 text-xs text-mute">A non-execution agent with any of these in live code fails the scan.</p>
          <p className="mt-3 flex flex-wrap gap-1">
            {policy.bannedPrimitives.map((p) => (
              <code key={p} className="border border-line px-1.5 py-0.5 font-pixel text-[9px] text-soft">
                {p}
              </code>
            ))}
          </p>
        </div>
        <div className="frame p-5">
          <h3 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Secret detection</h3>
          <p className="mt-2 text-xs text-mute">Key material or a credential assigned in code, config or docs fails the scan.</p>
          <ul className="mt-3 space-y-1 text-xs text-soft">
            {policy.secretPatterns.map((p) => (
              <li key={p} className="font-pixel text-[10px]">
                {p.replaceAll("_", " ")}
              </li>
            ))}
          </ul>
        </div>
        <div className="frame p-5">
          <h3 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Deviation, not advice</h3>
          <p className="mt-2 text-xs text-mute">Advice-shaped phrases in output code are held for review.</p>
          <p className="mt-3 flex flex-wrap gap-1">
            {policy.adviceTerms.map((p) => (
              <code key={p} className="border border-line px-1.5 py-0.5 text-[10px] text-soft">
                {p}
              </code>
            ))}
          </p>
        </div>
      </section>

      <section className="mt-4 frame p-5" aria-label="Trust ladder">
        <h3 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Trust ladder</h3>
        <p className="mt-2 text-xs text-mute">
          Trust {policy.trustNeedsEvidenceFrom} and above must be earned with detectors and tests, or the sentinel caps it to 1.
          {scan ? " Placement uses the effective trust from the last scan." : ""}
        </p>
        <div className="mt-4 grid gap-px bg-line sm:grid-cols-4">
          {[
            [0, "Sandboxed"],
            [1, "Read-only"],
            [2, "Scoped writes"],
            [3, "Platform"],
          ].map(([lvl, label]) => (
            <div key={lvl} className="bg-bg p-4">
              <p className="font-pixel text-2xl text-ink">{lvl}</p>
              <p className="text-[11px] text-mute">{label}</p>
              <p className="mt-3 flex flex-wrap gap-1.5">
                {agents
                  .filter((a) => trustOf(a) === lvl)
                  .map((a) => (
                    <span key={a.id} className="font-pixel text-[10px] text-accent-hi">
                      {a.id}
                    </span>
                  ))}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-4 frame p-5" aria-label="Approval queue">
        <h3 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Approval queue</h3>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-soft">
          Empty — and not because nothing is waiting. When the bus holds an action it returns{" "}
          <code className="font-pixel text-[10px]">held</code> to the sender and writes a{" "}
          <code className="font-pixel text-[10px]">gate_hold</code> entry to its in-memory trace. Nothing persists held actions
          yet, so there is nothing here to approve or reject. Once the bus is wired to the live kernel (SP-4), held actions will
          land here with approve / reject.
        </p>
      </section>
    </>
  );
}

function ScanDetail({ a }: { a: AgentScan }) {
  return (
    <tr className="border-t border-line bg-white/[0.02]">
      <td colSpan={3 + CHECKS.length} className="px-3 py-4">
        <p className="mb-3 text-[11px] text-mute">
          <code className="font-pixel text-[10px]">{a.dir}</code>
        </p>
        <ul className="grid gap-2 md:grid-cols-2">
          {a.checks.map((c) => (
            <li key={c.check} className="text-xs">
              <span className="font-pixel text-[10px] text-ink capitalize">{c.check}</span>
              <span className="ml-2 text-soft">{c.summary}</span>
              {FILE_SCANS.has(c.check) && <span className="ml-2 text-mute">· {c.scanned} files</span>}
              {c.evidence.length > 0 && (
                <ul className="mt-1 space-y-0.5 pl-3 font-pixel text-[9px] text-mute">
                  {c.evidence.slice(0, 8).map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </td>
    </tr>
  );
}
