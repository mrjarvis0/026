import type { Metadata } from "next";
import { AgentsView } from "@/components/AgentsView";
import { Footer, Nav } from "@/components/Nav";
import { Reveal } from "@/components/Reveal";
import { fleetStats, loadFleet } from "@/lib/fleet";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "agents — 026" };

export default async function AgentsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const [agents, { id }] = await Promise.all([loadFleet(), searchParams]);
  const stats = fleetStats(agents);
  const initialId = agents.some((a) => a.id === id) ? String(id) : agents[0].id;

  return (
    <>
      <Nav current="agents" />
      <main className="mx-auto max-w-7xl px-4 pt-28 pb-16 sm:px-6">
        <Reveal>
          <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">§2 · Agent manifests</p>
          <h1 className="mt-4 text-5xl font-medium tracking-tight text-ink sm:text-6xl">
            Agents. <span className="font-serif text-[1.1em] italic text-accent-hi">Every contract, in full.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-soft">
            Each agent exactly as its manifest declares it — tools, detectors, trust, memory and charter —
            read on every request. {stats.total} agents: {stats.registered} registered, {stats.planned} still
            specs. {stats.detectors} detectors, {stats.validated} validated.
          </p>
        </Reveal>
        <AgentsView agents={agents} initialId={initialId} />
      </main>
      <Footer current="agents" />
    </>
  );
}
