"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";
import type { Agent } from "@/lib/fleet";
import { MATURITY_COLOR, count, toolAccess, type Maturity } from "@/lib/maturity";
import type { Part } from "./AgentModel";

const AgentModel = dynamic(() => import("./AgentModel"), { ssr: false });

// AGENTS.md §6
const TRUST: Record<number, string> = {
  0: "Sandboxed — reasoning only",
  1: "Read-only — no side effects",
  2: "Scoped writes — declared surface",
  3: "Platform — human-adjacent",
};

function Chip({ status }: { status: Maturity }) {
  return (
    <span className="flex items-center gap-1.5 font-pixel text-[9px] uppercase text-soft">
      <span
        className={`size-2 ${status === "planned" ? "border border-dashed border-mute" : ""}`}
        style={status === "planned" ? undefined : { background: MATURITY_COLOR[status] }}
      />
      {status}
    </span>
  );
}

function StateIcon({ ok }: { ok: boolean }) {
  return ok ? (
    <svg viewBox="0 0 16 16" className="size-3.5 shrink-0 text-good" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M3 8.5 6.5 12 13 4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ) : (
    <svg viewBox="0 0 16 16" className="size-3.5 shrink-0 text-warning" fill="currentColor" aria-hidden>
      <path d="M8 1.5 15 14H1L8 1.5Zm-.75 5v4h1.5v-4h-1.5Zm0 5v1.5h1.5V11.5h-1.5Z" />
    </svg>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line pt-6">
      <h3 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">{title}</h3>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function AgentsView({ agents, initialId }: { agents: Agent[]; initialId: string }) {
  const still = !!useReducedMotion();
  const [id, setId] = useState(initialId);
  const [highlight, setHighlight] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const agent = agents.find((a) => a.id === id) ?? agents[0];

  // Mobile roster is a horizontal strip: bring the selected agent into it without scrolling the page.
  useEffect(() => {
    const li = document.querySelector(`[data-agent="${id}"]`);
    const ul = li?.closest("ul");
    if (li && ul) ul.scrollLeft += li.getBoundingClientRect().left - ul.getBoundingClientRect().left - 8;
  }, [id]);

  const select = (next: string) => {
    setId(next);
    setPicked(null);
    history.replaceState(null, "", `?id=${next}`);
  };
  // Picking in 3D shows the part's facts in place; the page only scrolls when asked to.
  const pick = (p: Part) => setPicked(p.kind === "stage" ? null : p.id);
  const pickedDetector = agent.detectors.find((d) => d.id === picked);
  const pickedTool = agent.tools.find((t) => t === picked);
  const rowProps = (partId: string) => ({
    id: `part-${partId}`,
    onMouseEnter: () => setHighlight(partId),
    onMouseLeave: () => setHighlight(null),
    className: `border-t border-line transition-colors ${picked === partId ? "bg-accent/10" : "hover:bg-white/[0.03]"}`,
  });

  const groups = [
    { label: "Registered", list: agents.filter((a) => a.registered) },
    { label: "Planned", list: agents.filter((a) => !a.registered) },
  ];

  return (
    <div className="mt-12 grid grid-cols-1 gap-8 lg:grid-cols-[280px_minmax(0,1fr)]">
      <nav aria-label="Agent roster" className="min-w-0 lg:sticky lg:top-20 lg:max-h-[calc(100svh-6rem)] lg:self-start lg:overflow-y-auto">
        {groups.map((g) => (
          <div key={g.label} className="mb-6">
            <p className="mb-2 text-[11px] text-mute">
              {g.label} · {g.list.length}
            </p>
            <ul className="flex gap-1 overflow-x-auto pb-1 [scrollbar-width:thin] lg:grid lg:grid-cols-1 lg:overflow-visible">
              {g.list.map((a) => (
                <li key={a.id} data-agent={a.id} className="w-52 shrink-0 lg:w-auto">
                  <button
                    type="button"
                    onClick={() => select(a.id)}
                    aria-current={a.id === agent.id ? "true" : undefined}
                    className={`flex w-full items-center gap-3 border px-3 py-2 text-left transition-colors ${a.id === agent.id ? "border-accent/60 bg-accent/10" : "border-transparent hover:border-line"} ${a.registered ? "" : "opacity-70"}`}
                  >
                    <span className="w-9 shrink-0 font-pixel text-xs text-accent-hi">{a.id}</span>
                    <span className="min-w-0 flex-1 truncate text-[13px] text-ink">{a.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="min-w-0">
        <div className="frame relative h-[420px] overflow-hidden bg-panel/40 sm:h-[480px]">
          <AgentModel agent={agent} highlight={highlight} onPick={pick} still={still} />
          <div className="pointer-events-none absolute top-4 left-5">
            <p className="font-pixel text-4xl text-ink">{agent.id}</p>
            <p className="mt-1 text-[15px] text-ink">{agent.name}</p>
            <div className="mt-2">
              <Chip status={agent.status} />
            </div>
          </div>
          {(pickedDetector || pickedTool) && (
            <div className="frame absolute bottom-12 left-4 w-72 bg-panel/90 p-4 text-xs backdrop-blur-md">
              <div className="flex items-start justify-between gap-3">
                <p className="font-pixel text-[11px] text-ink">{picked}</p>
                <button type="button" onClick={() => setPicked(null)} aria-label="Close" className="text-mute hover:text-ink">
                  ✕
                </button>
              </div>
              {pickedDetector ? (
                <>
                  <p className="mt-2 flex items-center gap-1.5 text-soft">
                    <StateIcon ok={pickedDetector.maturity === "validated"} />
                    {pickedDetector.maturity === "validated" ? "Validated — may alert" : `${pickedDetector.maturity} — muted, cannot alert`}
                  </p>
                  {pickedDetector.ceiling != null && (
                    <p className="mt-1 text-mute">Confidence ceiling {pickedDetector.ceiling.toFixed(2)}</p>
                  )}
                  {pickedDetector.note && <p className="mt-1 text-mute">{pickedDetector.note}</p>}
                </>
              ) : (
                <p className="mt-2 text-soft">Typed tool · {toolAccess(pickedTool!)} access</p>
              )}
              <button
                type="button"
                onClick={() =>
                  document.getElementById(`part-${picked}`)?.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "center" })
                }
                className="mt-3 text-accent hover:text-accent-hi"
              >
                See in contract ↓
              </button>
            </div>
          )}
          <ul className="pointer-events-none absolute bottom-3 left-4 hidden max-w-md flex-wrap gap-x-4 gap-y-1 text-[11px] text-mute sm:flex">
            <li>▭ pipeline layers (the contract&apos;s shape, not build status)</li>
            <li className="text-accent">■ tools</li>
            <li className="text-warning">◇ detectors — hollow = implemented, solid = validated</li>
            <li>◯ base rings = trust level</li>
            {agent.execution && <li className="text-serious">◯ execution-gated</li>}
          </ul>
        </div>

        <div className="mt-8 space-y-8">
          {agent.registered ? <Contract agent={agent} rowProps={rowProps} /> : <Spec agent={agent} />}
        </div>
      </div>
    </div>
  );
}

function Contract({ agent, rowProps }: { agent: Agent; rowProps: (id: string) => object }) {
  const facts: [string, string, boolean | null][] = [
    ["Trust level", `${agent.trust} · ${TRUST[agent.trust ?? 0]}`, null],
    ["Kernel-wired", agent.kernelWired ? "Yes — on the shared bus" : "No — standalone", agent.kernelWired],
    ["Runtime-verified", agent.runtimeVerified ? "Yes — tests pass" : "Not yet", agent.runtimeVerified],
    ...Object.entries(agent.invariants).map(([k, v]): [string, string, boolean | null] => [
      k.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase()),
      k === "execution_enabled" && v ? "Yes — behind the sentinel gate" : v ? "Yes" : "No",
      null,
    ]),
    [
      "Model",
      !agent.model
        ? "—"
        : agent.model.tier === "none"
          ? `No LLM — ${agent.model.note ?? ""}`
          : `${agent.model.tier}${agent.model.fallback ? ` → ${agent.model.fallback}` : ""}${agent.model.temperature != null ? ` · temp ${agent.model.temperature}` : ""}`,
      null,
    ],
  ];

  return (
    <>
      <div>
        <p className="text-[15px] leading-relaxed text-ink">{agent.role}</p>
        <p className="mt-3 text-xs text-mute">
          {agent.domain} · v{agent.version} · {count(agent.tools.length, "tool")} ·{" "}
          {count(agent.detectors.length, "detector")}
        </p>
      </div>

      <dl className="grid gap-px bg-line sm:grid-cols-2">
        {facts.map(([k, v, ok]) => (
          <div key={k} className="bg-bg p-4">
            <dt className="text-[11px] text-mute">{k}</dt>
            <dd className="mt-1 flex items-start gap-2 text-sm text-ink">
              {ok !== null && <StateIcon ok={ok} />}
              {v}
            </dd>
          </div>
        ))}
      </dl>

      <Section title={`Tools · ${agent.tools.length}`}>
        {agent.tools.length ? (
          <table className="w-full text-left text-sm">
            <thead className="text-[11px] text-mute">
              <tr>
                <th className="py-2 font-normal">Tool</th>
                <th className="py-2 font-normal">Access</th>
              </tr>
            </thead>
            <tbody>
              {agent.tools.map((t) => (
                <tr key={t} {...rowProps(t)}>
                  <td className="py-2.5 font-pixel text-xs text-accent-hi">{t}</td>
                  <td className="py-2.5 text-soft">{toolAccess(t)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-mute">No typed tools declared in the manifest yet.</p>
        )}
      </Section>

      <Section title={`Detectors · ${agent.detectors.length}`}>
        {agent.detectors.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="text-[11px] text-mute">
                <tr>
                  <th className="py-2 font-normal">Detector</th>
                  <th className="py-2 font-normal">Maturity</th>
                  <th className="py-2 font-normal">Ceiling</th>
                  <th className="py-2 font-normal">Note</th>
                </tr>
              </thead>
              <tbody>
                {agent.detectors.map((d) => (
                  <tr key={d.id} {...rowProps(d.id)}>
                    <td className="py-2.5 pr-4 font-pixel text-xs whitespace-nowrap text-ink">{d.id}</td>
                    <td className="py-2.5 pr-4">
                      <span className="flex items-center gap-1.5 text-soft">
                        <StateIcon ok={d.maturity === "validated"} />
                        {d.maturity === "validated" ? "Validated · may alert" : `${d.maturity} · muted`}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 text-soft tabular-nums">{d.ceiling?.toFixed(2) ?? "—"}</td>
                    <td className="py-2.5 text-xs text-mute">{d.note ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="flex items-center gap-2 text-sm text-mute">
            <StateIcon ok={false} />
            No detectors — this agent cannot alert, and cannot leave trust level 1 (AGENTS.md §2).
          </p>
        )}
      </Section>

      <div className="grid gap-8 md:grid-cols-2">
        <Section title="Memory · brain namespaces">
          {(["reads", "writes"] as const).map((k) => (
            <p key={k} className="mb-3 flex flex-wrap items-center gap-1.5 text-xs">
              <span className="w-12 text-mute">{k}</span>
              {agent.memory[k].length ? (
                agent.memory[k].map((ns) => (
                  <span key={ns} className="border border-line px-2 py-0.5 font-pixel text-[10px] text-soft">
                    {ns}
                  </span>
                ))
              ) : (
                <span className="text-mute">none declared</span>
              )}
            </p>
          ))}
        </Section>
        <Section title="Held for operator approval">
          {agent.requiresApproval.length ? (
            <p className="flex flex-wrap gap-1.5">
              {agent.requiresApproval.map((a) => (
                <span key={a} className="flex items-center gap-1.5 border border-serious/40 px-2 py-0.5 font-pixel text-[10px] text-serious">
                  <svg viewBox="0 0 16 16" className="size-3" fill="currentColor" aria-hidden>
                    <path d="M5 7V5a3 3 0 0 1 6 0v2h1v7H4V7h1Zm1.5 0h3V5a1.5 1.5 0 0 0-3 0v2Z" />
                  </svg>
                  {a}
                </span>
              ))}
            </p>
          ) : (
            <p className="text-sm text-mute">None declared in the manifest.</p>
          )}
        </Section>
      </div>

      <Section title="Charter">
        <ul className="space-y-2">
          {agent.charter.map((line) => (
            <li key={line} className="flex gap-3 text-sm leading-relaxed text-soft">
              <span className="text-accent">—</span>
              {line}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Provenance">
        <p className="text-sm text-soft">{agent.origin || "—"}</p>
        <p className="mt-2 text-xs text-mute">
          Read from <code className="font-pixel text-[10px] text-soft">{agent.source}</code> and{" "}
          <code className="font-pixel text-[10px] text-soft">config/agents/registry.yaml</code> on this request.
        </p>
      </Section>
    </>
  );
}

function Spec({ agent }: { agent: Agent }) {
  return (
    <>
      <p className="flex items-start gap-2 text-sm text-soft">
        <StateIcon ok={false} />
        Spec only — no manifest, no code, not in the registry. It cannot run, read or alert yet.
      </p>
      {agent.spec?.meta && <p className="text-xs text-mute">{agent.spec.meta}</p>}
      {agent.spec?.summary && <p className="text-[15px] leading-relaxed text-ink">{agent.spec.summary}</p>}
      <Section title="To join the fleet it needs">
        <ul className="space-y-2 text-sm text-soft">
          <li>— an <code className="font-pixel text-[10px]">agent.yaml</code> manifest (AGENTS.md §2)</li>
          <li>— an entry in <code className="font-pixel text-[10px]">config/agents/registry.yaml</code></li>
          <li>— detectors with behaviour, regression and architecture tests (§10) to leave trust level 1</li>
        </ul>
        <p className="mt-4 text-xs text-mute">
          Read from <code className="font-pixel text-[10px] text-soft">{agent.source}</code>.
        </p>
      </Section>
    </>
  );
}
