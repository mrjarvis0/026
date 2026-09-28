"use client";

import dynamic from "next/dynamic";
import { Fragment, useState } from "react";
import { useReducedMotion } from "motion/react";
import type { RoundMessage, RoundResult, TraceEntry } from "@/lib/trace";
import { BUS_STATUS_COLOR as STATUS_COLOR } from "@/lib/status";

const BusFlight = dynamic(() => import("./BusFlight"), { ssr: false });

export type TraceAgent = { id: string; name: string; tools: string[]; approvals: string[] };
type Round = { n: number; at: string; results: RoundResult[]; trace: TraceEntry[] };

const UNDECLARED = "undeclared.tool";
const MAX = 12;

// One message down every path the bus has: ok, held, denied, no_handler, degraded.
const SAMPLE: RoundMessage[] = [
  { to: "A001", type: "query", op: "detectors", budget: 100 },
  { to: "A002", type: "query", op: "stats", budget: 100 },
  { to: "A015", type: "query", op: "latest_events", budget: 100 },
  { to: "A002", type: "task.assign", op: "sources", budget: 100, action: { tool: "external.post", kind: "write" } },
  { to: "A001", type: "task.assign", op: "metrics", budget: 100, action: { tool: "rpc.call", kind: "trade" } },
  { to: "A007", type: "query", op: "", budget: 100 },
  { to: "A002", type: "query", op: "settings", budget: 0 },
];

function Status({ status }: { status: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink">
      <span className="size-2.5 shrink-0" style={{ background: STATUS_COLOR[status] ?? "#6b7280" }} />
      {status.replace("_", " ")}
    </span>
  );
}

const describe = (m: RoundMessage) =>
  `${m.to} · ${m.type} · ${m.op || "(no op)"}${m.action ? ` · action ${m.action.tool}/${m.action.kind}` : ""}${m.budget === 0 ? " · budget 0" : ""}`;

export function TraceView({
  agents,
  ops,
  executionKinds,
}: {
  agents: TraceAgent[];
  ops: Record<string, { key: string; values: string[] }>;
  executionKinds: string[];
}) {
  const still = !!useReducedMotion();
  const [to, setTo] = useState(agents[0]?.id ?? "");
  const agent = agents.find((a) => a.id === to)!;
  const opList = ops[to]?.values ?? [];
  const [op, setOp] = useState(opList[0] ?? "");
  const [type, setType] = useState<RoundMessage["type"]>("query");
  const [withAction, setWithAction] = useState(false);
  const toolList = [...new Set([...agent.tools, ...agent.approvals, UNDECLARED])];
  const [tool, setTool] = useState(toolList[0]);
  const [kind, setKind] = useState("read");
  const [exhausted, setExhausted] = useState(false);

  const [queue, setQueue] = useState<RoundMessage[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [play, setPlay] = useState(0);
  const [open, setOpen] = useState<string | null>(null);

  const pickTo = (id: string) => {
    const a = agents.find((x) => x.id === id);
    if (!a) return;
    setTo(id);
    setOp(ops[id]?.values[0] ?? "");
    setTool([...a.tools, ...a.approvals, UNDECLARED][0]);
  };

  const add = () =>
    setQueue((q) =>
      q.length >= MAX
        ? q
        : [...q, { to, type, op, budget: exhausted ? 0 : 100, action: withAction ? { tool, kind } : undefined }],
    );

  const runRound = async (messages: RoundMessage[]) => {
    setRunning(true);
    setError(null);
    try {
      const res = await fetch("/trace/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ messages }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setRounds((r) => [{ n: (r[0]?.n ?? 0) + 1, at: new Date().toLocaleTimeString(), ...data }, ...r]);
      setQueue([]);
      setPlay((p) => p + 1);
    } catch (e) {
      setError((e as Error).message || "The round failed.");
    } finally {
      setRunning(false);
    }
  };

  const latest = rounds[0];
  const onBus = new Set(Object.keys(ops));

  return (
    <>
      <p className="mt-8 flex max-w-3xl items-start gap-2 text-xs leading-relaxed text-soft">
        <svg viewBox="0 0 16 16" className="mt-px size-3.5 shrink-0 text-warning" fill="currentColor" aria-label="Note">
          <path d="M8 1.5 15 14H1L8 1.5Zm-.75 5v4h1.5v-4h-1.5Zm0 5v1.5h1.5V11.5h-1.5Z" />
        </svg>
        <span>
          The bus keeps its trace in memory only and no live kernel loop is sending traffic yet — so there is no history to
          show. Every entry here comes from messages you send through the real bus from this page (real gate, real budget,
          read-only adapters). Rounds live in this tab until you leave it.
        </span>
      </p>

      <section className="mt-8 grid gap-4 lg:grid-cols-[1.35fr_1fr]" aria-label="Bus round">
        <div className="frame relative h-[420px] overflow-hidden bg-panel/40 sm:h-[480px]">
          <BusFlight
            lanes={agents.map((a) => ({ id: a.id, onBus: onBus.has(a.id) }))}
            flights={(latest?.results ?? []).map((r) => ({ to: r.message.to, status: r.response.status }))}
            play={play}
            onPick={pickTo}
            still={still}
          />
          <div className="pointer-events-none absolute top-4 left-5">
            <p className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Orchestrator → gate → agent</p>
            <ul className="mt-2 flex max-w-xs flex-wrap gap-x-3 gap-y-1 text-[11px] text-mute">
              {Object.keys(STATUS_COLOR).map((s) => (
                <li key={s}>
                  <Status status={s} />
                </li>
              ))}
            </ul>
          </div>
          {latest && (
            <button
              type="button"
              onClick={() => setPlay((p) => p + 1)}
              onPointerDown={(e) => e.stopPropagation()}
              className="frame absolute bottom-3 left-4 bg-panel/80 px-3 py-1.5 text-xs text-ink hover:border-line-strong"
            >
              ▶ Replay round {latest.n}
            </button>
          )}
        </div>

        <div className="frame p-5">
          <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Compose a round</h2>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <label className="col-span-2 grid gap-1 text-[11px] text-mute">
              To
              <select value={to} onChange={(e) => pickTo(e.target.value)} className="border border-line bg-panel px-3 py-2 text-sm text-ink">
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.id} · {a.name}
                    {onBus.has(a.id) ? "" : " (no bus handler)"}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-[11px] text-mute">
              Type
              <select value={type} onChange={(e) => setType(e.target.value as RoundMessage["type"])} className="border border-line bg-panel px-3 py-2 text-sm text-ink">
                <option value="query">query</option>
                <option value="task.assign">task.assign</option>
              </select>
            </label>
            <label className="grid gap-1 text-[11px] text-mute">
              {ops[to]?.key ?? "op"}
              <select
                value={op}
                onChange={(e) => setOp(e.target.value)}
                disabled={!opList.length}
                className="border border-line bg-panel px-3 py-2 text-sm text-ink disabled:opacity-50"
              >
                {opList.length ? opList.map((o) => <option key={o}>{o}</option>) : <option value="">—</option>}
              </select>
            </label>
            <label className="col-span-2 flex items-center gap-2 text-xs text-soft">
              <input type="checkbox" checked={withAction} onChange={(e) => setWithAction(e.target.checked)} />
              Declare an action (the sentinel gate checks it)
            </label>
            {withAction && (
              <>
                <select value={tool} onChange={(e) => setTool(e.target.value)} aria-label="Action tool" className="border border-line bg-panel px-3 py-2 text-sm text-ink">
                  {toolList.map((t) => (
                    <option key={t} value={t}>
                      {t === UNDECLARED ? "undeclared tool" : `${t}${agent.approvals.includes(t) ? " (approval)" : ""}`}
                    </option>
                  ))}
                </select>
                <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Action kind" className="border border-line bg-panel px-3 py-2 text-sm text-ink">
                  <option value="read">read</option>
                  <option value="write">write</option>
                  <optgroup label="execution boundary">
                    {executionKinds.map((k) => (
                      <option key={k}>{k}</option>
                    ))}
                  </optgroup>
                </select>
              </>
            )}
            <label className="col-span-2 flex items-center gap-2 text-xs text-soft">
              <input type="checkbox" checked={exhausted} onChange={(e) => setExhausted(e.target.checked)} />
              Send with an exhausted budget (0 calls)
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" onClick={add} disabled={queue.length >= MAX} className="frame px-3 py-2 text-sm text-ink hover:border-line-strong disabled:opacity-50">
              + Add to round
            </button>
            <button
              type="button"
              onClick={() => runRound(SAMPLE)}
              disabled={running}
              className="px-3 py-2 text-sm text-accent hover:text-accent-hi disabled:opacity-50"
              title="One message down every path: ok, held, denied, no handler, degraded"
            >
              Run the sample round
            </button>
          </div>

          {queue.length > 0 && (
            <ol className="mt-4 space-y-1 border-t border-line pt-3 text-xs text-soft">
              {queue.map((m, i) => (
                <li key={i} className="flex items-center justify-between gap-3">
                  <span className="truncate">
                    {i + 1}. {describe(m)}
                  </span>
                  <button type="button" onClick={() => setQueue((q) => q.filter((_, j) => j !== i))} aria-label="Remove" className="text-mute hover:text-ink">
                    ✕
                  </button>
                </li>
              ))}
            </ol>
          )}
          <button
            type="button"
            onClick={() => runRound(queue)}
            disabled={!queue.length || running}
            className="mt-4 w-full bg-accent px-4 py-2.5 text-sm font-medium text-bg transition hover:bg-accent-hi disabled:opacity-50"
          >
            {running ? "Running through the bus…" : `Run round (${queue.length}/${MAX})`}
          </button>
          {error && <p className="mt-3 text-xs text-critical">{error}</p>}
        </div>
      </section>

      <section className="mt-14" aria-label="Trace log">
        <h2 className="text-2xl font-medium text-ink">Trace log</h2>
        {!rounds.length && (
          <p className="frame mt-4 p-8 text-center text-sm text-mute">
            No rounds yet. Run the sample round to see a message down every path the bus has.
          </p>
        )}
        {rounds.map((round) => (
          <div key={round.n} className="mt-6">
            <p className="text-xs text-mute">
              Round {round.n} · {round.at} · {round.results.length} messages · {round.trace.length} trace entries ·{" "}
              {round.results.reduce((s, r) => s + r.ms, 0).toFixed(0)} ms in handlers
            </p>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-[11px] text-mute">
                  <tr>
                    <th className="py-2 pr-3 font-normal">Status</th>
                    <th className="py-2 pr-3 font-normal">Message</th>
                    <th className="py-2 pr-3 font-normal">Reason</th>
                    <th className="py-2 pr-3 text-right font-normal">ms</th>
                    <th className="py-2 font-normal">Trace</th>
                  </tr>
                </thead>
                <tbody>
                  {round.results.map((r, i) => {
                    const key = `${round.n}-${i}`;
                    const entries = round.trace.filter((e) => e.trace_id === r.message.trace_id);
                    const t0 = entries.length ? new Date(entries[0].at).getTime() : 0;
                    return (
                      <Fragment key={key}>
                        <tr
                          onClick={() => setOpen((o) => (o === key ? null : key))}
                          aria-expanded={open === key}
                          className="cursor-pointer border-t border-line hover:bg-white/[0.03]"
                        >
                          <td className="py-2.5 pr-3">
                            <Status status={r.response.status} />
                          </td>
                          <td className="py-2.5 pr-3 text-xs text-soft">
                            <span className="font-pixel text-[11px] text-accent-hi">{r.message.to}</span> · {r.message.type} ·{" "}
                            {String(r.message.payload.op ?? r.message.payload.intent ?? "—")}
                            {r.message.action && ` · ${r.message.action.tool}/${r.message.action.kind}`}
                            {r.message.budget.calls === 0 && " · budget 0"}
                          </td>
                          <td className="py-2.5 pr-3 text-xs text-mute">{r.response.reason || "—"}</td>
                          <td className="py-2.5 pr-3 text-right text-xs text-soft tabular-nums">{r.ms}</td>
                          <td className="py-2.5 font-pixel text-[9px] text-mute">{r.message.trace_id}</td>
                        </tr>
                        {open === key && (
                          <tr className="border-t border-line bg-white/[0.02]">
                            <td colSpan={5} className="px-3 py-4">
                              <p className="text-[11px] text-mute">Replay of {r.message.trace_id} — what the bus recorded, in order:</p>
                              <ol className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                                {entries.map((e, j) => (
                                  <li key={j} className="flex items-center gap-2">
                                    {j > 0 && <span className="text-mute">→</span>}
                                    <span className="border border-line px-2 py-0.5 font-pixel text-[10px] text-ink">{e.kind}</span>
                                    <span className="text-[10px] text-mute tabular-nums">+{new Date(e.at).getTime() - t0} ms</span>
                                  </li>
                                ))}
                              </ol>
                              <pre className="mt-3 max-h-64 overflow-auto border border-line bg-bg p-3 text-[11px] leading-relaxed text-soft">
                                {JSON.stringify({ message: r.message, response: r.response }, null, 2)}
                              </pre>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </section>
    </>
  );
}
