import type { Metadata } from "next";
import { Footer, Nav } from "@/components/Nav";
import { OrchestratorAnatomy } from "@/components/OrchestratorAnatomy";
import { OrchestratorConsole } from "@/components/OrchestratorConsole";
import { Reveal } from "@/components/Reveal";
import { loadFleet } from "@/lib/fleet";
import { loadAnatomy } from "@/lib/orchestrator";
import { loadPolicy } from "@/lib/sentinel";
import { BUS_OPS } from "@/lib/trace";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "orchestrator — 026" };

function Built({ state }: { state: "built" | "partial" | "missing" }) {
  const map = {
    built: ["#0ca30c", "Built"],
    partial: ["#fab219", "Partial"],
    missing: ["#6b7280", "Not built"],
  } as const;
  const [color, label] = map[state];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink">
      <span className="size-2.5" style={{ background: color }} />
      {label}
    </span>
  );
}

export default async function OrchestratorPage() {
  const [{ modules, modelRoutingBytes }, fleet, policy] = await Promise.all([loadAnatomy(), loadFleet(), loadPolicy()]);
  const has = (name: string) => (modules.find((m) => m.name === name)?.bytes ?? 0) > 0;
  const registered = fleet.filter((a) => a.registered);
  const tiers = Object.entries(
    registered.reduce<Record<string, string[]>>((acc, a) => {
      const t = a.model?.tier ?? "undeclared";
      (acc[t] ??= []).push(a.id);
      return acc;
    }, {}),
  );

  // AGENTS.md §3 gives the orchestrator three jobs; each is judged by whether its code exists.
  const capabilities: { job: string; state: "built" | "partial" | "missing"; evidence: string }[] = [
    {
      job: "Plan — turn a question into tasks",
      state: has("core") || has("workflows") ? "partial" : "missing",
      evidence: "orchestrator/core/, orchestrator/workflows/",
    },
    {
      job: "Route — deliver each task to an agent",
      state: has("event_bus") ? (has("router") ? "built" : "partial") : "missing",
      evidence: "event_bus/bus.py delivers to a named agent; router/ that picks the agent is empty",
    },
    {
      job: "Fuse — combine answers (weakest input wins)",
      state: "missing",
      evidence: "no fusion module yet (AGENTS.md §4 rules are specified, not coded)",
    },
    { job: "Gate every action", state: "built", evidence: "bus.py calls security/sentinel/gate.check_action" },
    { job: "Budget every message", state: "built", evidence: "event_bus/message.py Budget — exhausted degrades" },
    { job: "Trace every message", state: "partial", evidence: "event_bus/trace.py — in memory only, not persisted" },
    { job: "Schedule recurring work", state: has("scheduler") ? "partial" : "missing", evidence: "orchestrator/scheduler/" },
  ];

  return (
    <>
      <Nav current="orchestrator" />
      <main className="mx-auto max-w-7xl px-4 pt-28 pb-16 sm:px-6">
        <Reveal>
          <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">§3 · Platform actor · trust 3</p>
          <h1 className="mt-4 text-5xl font-medium tracking-tight text-ink sm:text-6xl">
            Orchestrator. <span className="font-serif text-[1.1em] italic text-accent-hi">Plan, route, fuse.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-soft">
            It plans work, routes tasks and fuses agent results. Today only the routing half exists — the bus, its gate,
            budget and trace. Until the planner is built, the console below is how you route by hand.
          </p>
        </Reveal>

        <section className="mt-10" aria-label="Console">
          <OrchestratorConsole
            agents={registered.map((a) => ({ id: a.id, name: a.name }))}
            ops={BUS_OPS}
            kinds={policy.executionKinds}
          />
        </section>

        <section className="mt-16" aria-label="Capabilities">
          <h2 className="text-2xl font-medium text-ink">What the orchestrator can do today</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <tbody>
                {capabilities.map((c) => (
                  <tr key={c.job} className="border-t border-line">
                    <td className="py-3 pr-4 text-ink">{c.job}</td>
                    <td className="py-3 pr-4 whitespace-nowrap">
                      <Built state={c.state} />
                    </td>
                    <td className="py-3 text-xs text-mute">{c.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-16" aria-label="Anatomy">
          <h2 className="mb-4 text-2xl font-medium text-ink">Anatomy</h2>
          <OrchestratorAnatomy modules={modules} />
        </section>

        <section className="mt-16 frame p-5" aria-label="Model routing">
          <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Model routing</h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-soft">
            Agents ask for a tier; <code className="font-pixel text-[10px]">config/models/models.yaml</code> is meant to map it to a
            model (AGENTS.md §8).{" "}
            {modelRoutingBytes ? (
              <>That file has {modelRoutingBytes} bytes of routing config.</>
            ) : (
              <span className="text-warning">That file is empty — no tier is mapped to a model yet.</span>
            )}
          </p>
          <ul className="mt-4 grid gap-px bg-line sm:grid-cols-3">
            {tiers.map(([tier, ids]) => (
              <li key={tier} className="bg-bg p-4">
                <p className="font-pixel text-xs text-ink">{tier === "none" ? "no LLM" : tier}</p>
                <p className="mt-2 flex flex-wrap gap-1.5">
                  {ids.map((id) => (
                    <span key={id} className="font-pixel text-[10px] text-accent-hi">
                      {id}
                    </span>
                  ))}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </main>
      <Footer current="orchestrator" />
    </>
  );
}
