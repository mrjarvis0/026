import type { Metadata } from "next";
import { Footer, Nav } from "@/components/Nav";
import { Reveal } from "@/components/Reveal";
import { SentinelView, type GateAgent } from "@/components/SentinelView";
import { loadFleet } from "@/lib/fleet";
import { lastScan, loadPolicy } from "@/lib/sentinel";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "sentinel — 026" };

export default async function SentinelPage() {
  const [fleet, policy] = await Promise.all([loadFleet(), loadPolicy()]);
  const agents: GateAgent[] = fleet
    .filter((a) => a.registered)
    .map((a) => ({
      id: a.id,
      name: a.name,
      trust: a.trust,
      tools: a.tools,
      approvals: a.requiresApproval,
    }));

  return (
    <>
      <Nav current="sentinel" />
      <main className="mx-auto max-w-7xl px-4 pt-28 pb-16 sm:px-6">
        <Reveal>
          <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">§6 · Trust &amp; governance</p>
          <h1 className="mt-4 text-5xl font-medium tracking-tight text-ink sm:text-6xl">
            Sentinel. <span className="font-serif text-[1.1em] italic text-accent-hi">Nothing crosses unseen.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-soft">
            The sentinel sits over every action. It scans each agent against its declared contract, and at runtime it
            allows, holds or denies every action the bus carries — deny-by-default at the execution boundary.
          </p>
        </Reveal>
        <SentinelView agents={agents} policy={policy} initialScan={lastScan()} />
      </main>
      <Footer current="sentinel" />
    </>
  );
}
