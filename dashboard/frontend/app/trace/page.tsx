import type { Metadata } from "next";
import { Footer, Nav } from "@/components/Nav";
import { Reveal } from "@/components/Reveal";
import { TraceView, type TraceAgent } from "@/components/TraceView";
import { loadFleet } from "@/lib/fleet";
import { loadPolicy } from "@/lib/sentinel";
import { BUS_OPS } from "@/lib/trace";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "trace — 026" };

export default async function TracePage() {
  const [fleet, policy] = await Promise.all([loadFleet(), loadPolicy()]);
  const agents: TraceAgent[] = fleet
    .filter((a) => a.registered)
    .map((a) => ({ id: a.id, name: a.name, tools: a.tools, approvals: a.requiresApproval }));

  return (
    <>
      <Nav current="trace" />
      <main className="mx-auto max-w-7xl px-4 pt-28 pb-16 sm:px-6">
        <Reveal>
          <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">§5 · Communication protocol</p>
          <h1 className="mt-4 text-5xl font-medium tracking-tight text-ink sm:text-6xl">
            Trace. <span className="font-serif text-[1.1em] italic text-accent-hi">Every message, on the record.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-soft">
            Agents never call each other — everything passes through the bus, and every message is logged, gated,
            budgeted and replayable.
          </p>
        </Reveal>
        <TraceView agents={agents} ops={BUS_OPS} executionKinds={policy.executionKinds} />
      </main>
      <Footer current="trace" />
    </>
  );
}
