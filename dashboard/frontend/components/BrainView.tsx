"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useReducedMotion } from "motion/react";
import { STATE_COLOR } from "@/lib/status";
import type { MapAgent, MapSpace } from "./BrainMap";

const BrainMap = dynamic(() => import("./BrainMap"), { ssr: false });

type Agent = MapAgent & { name: string };
type Check = {
  decision: "allowed" | "denied" | "invalid";
  reason?: string;
  versions?: number[];
  history?: { version: number; by: string }[];
  reads?: { by: string }[];
};

function Cell({ r, w }: { r: boolean; w: boolean }) {
  if (!r && !w) return <span className="text-mute/50">—</span>;
  return (
    <span className="font-pixel text-[10px]">
      {r && <span className="text-soft">R</span>}
      {w && <span className="text-accent-hi">W</span>}
    </span>
  );
}

export function BrainView({ agents, spaces }: { agents: Agent[]; spaces: MapSpace[] }) {
  const still = !!useReducedMotion();
  const [focus, setFocus] = useState<string | null>(null);
  const [agentId, setAgentId] = useState(agents[0]?.id ?? "");
  const [op, setOp] = useState<"read" | "write">("write");
  const [namespace, setNamespace] = useState(spaces[0]?.ns.replace("/*", "/demo") ?? "global");
  const [busy, setBusy] = useState(false);
  const [check, setCheck] = useState<(Check & { asked: string }) | null>(null);
  const [error, setError] = useState<string | null>(null);

  const has = (a: Agent, ns: string, kind: "reads" | "writes") => a[kind].includes(ns);
  const focusAgent = agents.find((a) => a.id === focus);
  const focusSpace = spaces.find((s) => s.ns === focus);

  const orphans = spaces.filter((s) => s.writers.length === 0);
  // Shared = one agent's write can reach a different agent's read.
  const shared = spaces.filter((s) => s.readers.some((r) => s.writers.some((w) => w !== r)));
  const walled = spaces.filter((s) => s.writers.length > 0 && !shared.includes(s));
  const silent = agents.filter((a) => a.reads.length + a.writes.length === 0);

  const ask = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/brain/check", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ agent: agentId, op, namespace }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setCheck({ ...data, asked: `${agentId} ${op} ${namespace}` });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section className="mt-10 grid gap-4 lg:grid-cols-[1.35fr_1fr]" aria-label="Brain map">
        <div className="frame relative h-[420px] overflow-hidden bg-panel/40 sm:h-[480px]">
          <BrainMap agents={agents} spaces={spaces} focus={focus} onFocus={setFocus} still={still} />
          <ul className="pointer-events-none absolute top-4 left-5 space-y-1 text-[11px] text-mute">
            <li className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Memory contract</li>
            <li>inner ring = namespaces · outer ring = agents</li>
            <li>
              <span className="text-accent-hi">━ write</span> · <span>┄ read</span> · hollow = nobody writes it
            </li>
            <li>click a node to focus it</li>
          </ul>
        </div>

        <div className="frame p-5">
          {focusAgent ? (
            <>
              <p className="font-pixel text-sm text-accent-hi">{focusAgent.id}</p>
              <p className="text-sm text-ink">{focusAgent.name}</p>
              <p className="mt-4 text-[11px] text-mute">reads</p>
              <p className="mt-1 flex flex-wrap gap-1.5">{chips(focusAgent.reads)}</p>
              <p className="mt-3 text-[11px] text-mute">writes</p>
              <p className="mt-1 flex flex-wrap gap-1.5">{chips(focusAgent.writes)}</p>
            </>
          ) : focusSpace ? (
            <>
              <p className="font-pixel text-sm text-accent-hi">{focusSpace.ns}</p>
              <p className="mt-4 text-[11px] text-mute">written by</p>
              <p className="mt-1 flex flex-wrap gap-1.5">{chips(focusSpace.writers, "nobody — it stays empty")}</p>
              <p className="mt-3 text-[11px] text-mute">read by</p>
              <p className="mt-1 flex flex-wrap gap-1.5">{chips(focusSpace.readers)}</p>
            </>
          ) : (
            <>
              <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">What the contract says</h2>
              <ul className="mt-4 space-y-3 text-sm leading-relaxed text-soft">
                {orphans.length > 0 && (
                  <li>
                    <span className="text-warning">Read but never written:</span> {orphans.map((s) => s.ns).join(", ")} —
                    read by {Math.max(...orphans.map((s) => s.readers.length))} agents, but no manifest writes them (AGENTS.md
                    gives them to the librarian, which is not built).
                  </li>
                )}
                <li>
                  <span className="text-ink">Shared across agents:</span>{" "}
                  {shared.length ? shared.map((s) => s.ns).join(", ") : "none"} — where one agent&apos;s write can reach
                  another agent&apos;s read. This is the correlation layer&apos;s fuel.
                </li>
                {walled.length > 0 && (
                  <li>
                    <span className="text-ink">Written, read by no other agent:</span> {walled.map((s) => s.ns).join(", ")} —
                    each is its owner&apos;s alone.
                  </li>
                )}
                {silent.length > 0 && (
                  <li>
                    <span className="text-ink">No memory declared:</span> {silent.map((a) => a.id).join(", ")} — runs
                    standalone, off the brain.
                  </li>
                )}
              </ul>
            </>
          )}
        </div>
      </section>

      <section className="mt-12" aria-label="Access matrix">
        <h2 className="text-2xl font-medium text-ink">Access matrix</h2>
        <p className="mt-1 text-xs text-mute">From each agent&apos;s manifest (memory.reads / memory.writes). Hover to focus.</p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr>
                <th className="py-2 pr-3 text-[11px] font-normal text-mute">Agent</th>
                {spaces.map((s) => (
                  <th
                    key={s.ns}
                    onMouseEnter={() => setFocus(s.ns)}
                    onMouseLeave={() => setFocus(null)}
                    className={`px-2 py-2 font-pixel text-[10px] font-normal ${focus === s.ns ? "text-ink" : "text-soft"}`}
                  >
                    {s.ns}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {agents.map((a) => (
                <tr
                  key={a.id}
                  onMouseEnter={() => setFocus(a.id)}
                  onMouseLeave={() => setFocus(null)}
                  className={`border-t border-line ${focus === a.id ? "bg-white/[0.03]" : ""}`}
                >
                  <td className="py-2.5 pr-3 font-pixel text-xs text-accent-hi">{a.id}</td>
                  {spaces.map((s) => (
                    <td key={s.ns} className={`px-2 py-2.5 ${focus === s.ns ? "bg-white/[0.03]" : ""}`}>
                      <Cell r={has(a, s.ns, "reads")} w={has(a, s.ns, "writes")} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-12 frame p-5" aria-label="Ask the brain">
        <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Ask the brain</h2>
        <p className="mt-2 max-w-3xl text-xs leading-relaxed text-mute">
          Runs the real access layer (<code className="font-pixel text-[10px]">brain.AgentBrainView</code>) against a throwaway
          in-memory brain — nothing is stored. An allowed write is made twice to show versioning; an allowed read shows the
          read being logged.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="grid gap-1 text-[11px] text-mute">
            Agent
            <select value={agentId} onChange={(e) => setAgentId(e.target.value)} className="border border-line bg-panel px-3 py-2 text-sm text-ink">
              {agents.map((a) => (
                <option key={a.id}>{a.id}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-[11px] text-mute">
            Op
            <select value={op} onChange={(e) => setOp(e.target.value as "read" | "write")} className="border border-line bg-panel px-3 py-2 text-sm text-ink">
              <option value="write">write</option>
              <option value="read">read</option>
            </select>
          </label>
          <label className="grid min-w-48 flex-1 gap-1 text-[11px] text-mute">
            Namespace
            <input
              value={namespace}
              onChange={(e) => setNamespace(e.target.value.trim())}
              list="brain-namespaces"
              spellCheck={false}
              className="border border-line bg-transparent px-3 py-2 font-pixel text-xs text-ink focus:border-accent focus:outline-none"
            />
            <datalist id="brain-namespaces">
              {spaces.map((s) => (
                <option key={s.ns} value={s.ns.replace("/*", "/demo")} />
              ))}
              {agents.map((a) => (
                <option key={a.id} value={`private/${a.id}`} />
              ))}
            </datalist>
          </label>
          <button
            type="button"
            onClick={ask}
            disabled={busy || !namespace}
            className="bg-accent px-4 py-2.5 text-sm font-medium text-bg transition hover:bg-accent-hi disabled:opacity-50"
          >
            {busy ? "Asking…" : "Check access"}
          </button>
        </div>
        <div aria-live="polite" className="mt-4 min-h-10 text-sm">
          {error && <p className="text-xs text-critical">{error}</p>}
          {check && !error && (
            <div className="border-t border-line pt-3">
              <p className="flex items-center gap-2">
                <span className="size-2.5" style={{ background: STATE_COLOR[check.decision === "allowed" ? "allow" : "deny"] }} />
                <span className="uppercase text-ink">{check.decision}</span>
                <span className="font-pixel text-[10px] text-mute">{check.asked}</span>
              </p>
              {check.reason && <p className="mt-1 text-xs text-soft">{check.reason}</p>}
              {check.versions && (
                <p className="mt-1 text-xs text-soft">
                  Two writes → versions {check.versions.join(" → ")}. Nothing is overwritten; the history keeps both
                  {check.history ? ` (by ${check.history.map((h) => h.by).join(", ")})` : ""}.
                </p>
              )}
              {check.reads && (
                <p className="mt-1 text-xs text-soft">
                  Read returned nothing (the brain is empty) — and the read itself was logged ({check.reads.length} entry, by{" "}
                  {check.reads.map((r) => r.by).join(", ")}).
                </p>
              )}
            </div>
          )}
        </div>
      </section>
    </>
  );
}

function chips(list: string[], empty = "none") {
  return list.length ? (
    list.map((x) => (
      <span key={x} className="border border-line px-2 py-0.5 font-pixel text-[10px] text-soft">
        {x}
      </span>
    ))
  ) : (
    <span className="text-xs text-mute">{empty}</span>
  );
}
