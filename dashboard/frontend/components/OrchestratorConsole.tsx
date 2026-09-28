"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { BUS_STATUS_COLOR, STATE_COLOR } from "@/lib/status";
import { PAGES as NAV_PAGES } from "./Nav";

type Line =
  | { kind: "cmd"; text: string }
  | { kind: "text"; text: string; tone?: "mute" | "ink" | "warn" }
  | { kind: "status"; status: string; color: string; text: string; detail?: string };

type ConsoleAgent = { id: string; name: string };

const PAGES = NAV_PAGES.map((p) => p.slug);
const COMMANDS = ["help", "agents", "gate", "scan", "open", "clear"];

const HELP: string[] = [
  "<ID> <op>                 send a read-only query through the bus     e.g. A001 detectors",
  "<ID>                      list what that agent answers on the bus",
  "gate <ID> <tool> <kind>   ask the sentinel gate                      e.g. gate A002 external.post write",
  "scan                      run the sentinel conformance scan",
  "agents                    registered agents and who is on the bus",
  "open <page>               go to a page                               e.g. open narratives",
  "clear                     clear the screen      ·  ↑ ↓ history  ·  Tab completes",
];

export function OrchestratorConsole({
  agents,
  ops,
  kinds,
}: {
  agents: ConsoleAgent[];
  ops: Record<string, { key: string; values: string[] }>;
  kinds: string[];
}) {
  const router = useRouter();
  const [lines, setLines] = useState<Line[]>([
    { kind: "text", text: "026 orchestrator console — the planner is not built yet, so you route by hand.", tone: "ink" },
    { kind: "text", text: "Every command runs for real: the bus, the sentinel gate, the conformance scan. Type help.", tone: "mute" },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const history = useRef<string[]>([]);
  const cursor = useRef(-1);
  const screen = useRef<HTMLDivElement>(null);
  const field = useRef<HTMLInputElement>(null);
  const ids = agents.map((a) => a.id);

  useEffect(() => {
    screen.current?.scrollTo({ top: screen.current.scrollHeight });
  }, [lines, busy]);

  const print = (...l: Line[]) => setLines((prev) => [...prev, ...l]);

  const post = async (url: string, body?: unknown) => {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error ?? `HTTP ${res.status}`);
    return data;
  };

  async function execute(raw: string) {
    // Bloomberg habit: a trailing <GO> is accepted and ignored.
    const words = raw.trim().split(/\s+/).filter((w) => !/^<?go>?$/i.test(w));
    const [head = "", ...rest] = words;
    const cmd = head.toLowerCase();
    const id = head.toUpperCase();

    if (!cmd) return;
    if (cmd === "help") return print(...HELP.map((t) => ({ kind: "text" as const, text: t, tone: "mute" as const })));
    if (cmd === "clear") return setLines([]);
    if (cmd === "agents") {
      return print(
        ...agents.map((a) => ({
          kind: "text" as const,
          text: `${a.id.padEnd(6)}${a.name.padEnd(42)}${ops[a.id] ? `on the bus · ${ops[a.id].values.join(", ")}` : "no bus handler yet"}`,
          tone: ops[a.id] ? ("ink" as const) : ("mute" as const),
        })),
      );
    }
    if (cmd === "open") {
      const page = (rest[0] ?? "").toLowerCase();
      if (!PAGES.includes(page)) return print({ kind: "text", text: `open what? ${PAGES.join(" · ")}`, tone: "warn" });
      const href = NAV_PAGES.find((p) => p.slug === page)!.href;
      print({ kind: "text", text: `→ ${href}`, tone: "mute" });
      return router.push(href);
    }
    if (cmd === "gate") {
      const [agent = "", tool = "", kind = ""] = rest;
      if (!agent || !tool || !kind) {
        return print({ kind: "text", text: `usage: gate <ID> <tool> <kind>   kinds: read, write, ${kinds.join(", ")}`, tone: "warn" });
      }
      const r = await post("/sentinel/gate", { agent: agent.toUpperCase(), tool, kind });
      return print({ kind: "status", status: r.decision, color: STATE_COLOR[r.decision], text: r.reason });
    }
    if (cmd === "scan") {
      print({ kind: "text", text: "running python -m security.sentinel scan — this can take a while…", tone: "mute" });
      const r = await post("/sentinel/scan");
      print({ kind: "status", status: r.verdict, color: STATE_COLOR[r.verdict], text: `fleet verdict · ${r.agents.length} agents · ${(r.durationMs / 1000).toFixed(1)} s` });
      return print(
        ...r.agents.map((a: { id: string; verdict: string; effective_trust: number }) => ({
          kind: "status" as const,
          status: a.verdict,
          color: STATE_COLOR[a.verdict],
          text: `${a.id} · effective trust ${a.effective_trust}`,
        })),
        { kind: "text", text: "details: open sentinel", tone: "mute" },
      );
    }
    if (ids.includes(id)) {
      const op = rest[0]?.toLowerCase() ?? "";
      if (!op) {
        return print({
          kind: "text",
          text: ops[id] ? `${id} answers: ${ops[id].values.join(" · ")}` : `${id} has no bus handler yet — a message would come back no_handler.`,
          tone: ops[id] ? "ink" : "mute",
        });
      }
      const { results } = await post("/trace/run", { messages: [{ to: id, type: "query", op, budget: 100 }] });
      const r = results[0];
      const payload = JSON.stringify(r.response.payload);
      return print({
        kind: "status",
        status: r.response.status,
        color: BUS_STATUS_COLOR[r.response.status] ?? "#6b7280",
        text: `${id} ${op} · ${r.ms} ms · ${r.message.trace_id}${r.response.reason ? ` · ${r.response.reason}` : ""}`,
        detail: payload === "{}" ? undefined : JSON.stringify(r.response.payload, null, 2),
      });
    }
    print({ kind: "text", text: `unknown command "${head}" — type help`, tone: "warn" });
  }

  const submit = async () => {
    const raw = input;
    if (!raw.trim() || busy) return;
    history.current = [raw, ...history.current.filter((h) => h !== raw)].slice(0, 50);
    cursor.current = -1;
    setInput("");
    print({ kind: "cmd", text: raw });
    setBusy(true);
    try {
      await execute(raw);
    } catch (e) {
      print({ kind: "text", text: `error: ${(e as Error).message}`, tone: "warn" });
    } finally {
      setBusy(false);
      field.current?.focus();
    }
  };

  const complete = () => {
    const words = input.split(/\s+/);
    const last = words.length - 1;
    const pool =
      last === 0
        ? [...COMMANDS, ...ids]
        : words[0].toLowerCase() === "open"
          ? PAGES
          : words[0].toLowerCase() === "gate" && last === 1
            ? ids
            : last === 1
              ? ops[words[0].toUpperCase()]?.values ?? []
              : [];
    const hits = pool.filter((p) => p.toLowerCase().startsWith(words[last].toLowerCase()));
    if (hits.length === 1) {
      words[last] = hits[0];
      setInput(words.join(" ") + " ");
    } else if (hits.length > 1) {
      print({ kind: "text", text: hits.join("   "), tone: "mute" });
    }
  };

  return (
    <div className="frame flex h-[520px] flex-col bg-panel/60" onClick={() => field.current?.focus()}>
      <div ref={screen} className="min-h-0 flex-1 space-y-1 overflow-y-auto p-5 font-pixel text-[12px] leading-relaxed" aria-live="polite">
        {lines.map((l, i) =>
          l.kind === "cmd" ? (
            <p key={i} className="pt-2 text-ink">
              <span className="text-accent">026&gt;</span> {l.text}
            </p>
          ) : l.kind === "text" ? (
            <p key={i} className={`whitespace-pre-wrap ${l.tone === "warn" ? "text-warning" : l.tone === "ink" ? "text-ink" : "text-mute"}`}>
              {l.text}
            </p>
          ) : (
            <div key={i}>
              <p className="flex items-start gap-2 text-soft">
                <span className="shrink-0 uppercase" style={{ color: l.color }}>
                  [{l.status}]
                </span>
                <span className="break-all">{l.text}</span>
              </p>
              {l.detail && (
                <details className="ml-4">
                  <summary className="cursor-pointer text-mute hover:text-soft">payload</summary>
                  <pre className="mt-1 max-h-60 overflow-auto border border-line bg-bg p-2 text-[11px] text-soft">{l.detail}</pre>
                </details>
              )}
            </div>
          ),
        )}
        {busy && <p className="animate-pulse text-mute">routing…</p>}
      </div>
      <label className="flex items-center gap-2 border-t border-line px-5 py-3 font-pixel text-[13px]">
        <span className="text-accent">026&gt;</span>
        <input
          ref={field}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
            else if (e.key === "Tab") {
              e.preventDefault();
              complete();
            } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
              e.preventDefault();
              const next = Math.max(-1, Math.min(history.current.length - 1, cursor.current + (e.key === "ArrowUp" ? 1 : -1)));
              cursor.current = next;
              setInput(next < 0 ? "" : history.current[next]);
            }
          }}
          disabled={busy}
          spellCheck={false}
          autoComplete="off"
          aria-label="Orchestrator command"
          placeholder="A001 detectors"
          className="min-w-0 flex-1 bg-transparent text-ink placeholder:text-mute/60 focus:outline-none"
        />
      </label>
    </div>
  );
}
