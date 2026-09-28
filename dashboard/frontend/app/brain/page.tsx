import type { Metadata } from "next";
import { BrainView } from "@/components/BrainView";
import { Footer, Nav } from "@/components/Nav";
import { Reveal } from "@/components/Reveal";
import { brainMap, brainStatus } from "@/lib/brain";
import { loadFleet } from "@/lib/fleet";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "brain — 026" };

function State({ ok, label }: { ok: boolean | null; label: string }) {
  const color = ok === null ? "#6b7280" : ok ? "#0ca30c" : "#fab219";
  return (
    <span className="inline-flex items-center gap-1.5 text-xs whitespace-nowrap text-ink">
      <span className="size-2.5" style={{ background: color }} />
      {label}
    </span>
  );
}

export default async function BrainPage() {
  const [fleet, status] = await Promise.all([loadFleet(), brainStatus()]);
  const { agents, spaces } = brainMap(fleet);
  const persistent = status.persistentCallers.length > 0;

  const parts: { part: string; ok: boolean | null; label: string; evidence: string }[] = [
    { part: "Versioned store — a write never overwrites", ok: true, label: "Built", evidence: "brain/store.py (sqlite3), brain/tests/test_brain.py" },
    { part: "Logged reads — nothing is silent", ok: true, label: "Built", evidence: "brain/store.py read_log" },
    { part: "Manifest-scoped access", ok: true, label: "Built", evidence: "brain/access.py AgentBrainView — deny outside memory.reads / writes" },
    {
      part: "Persistence — a brain on disk",
      ok: persistent,
      label: persistent ? "Wired" : "Not wired",
      evidence: persistent
        ? status.persistentCallers.join(", ")
        : "no Brain(<path>) outside tests — every brain is in-memory, so no record survives",
    },
    { part: "Librarian — curates global and entities", ok: null, label: "Not built", evidence: "platform actor in AGENTS.md §3; no code yet" },
    { part: "Embeddings · RAG · knowledge graph", ok: null, label: "Not built", evidence: "planned (docs/STACK.md: pgvector)" },
    {
      part: "Shared system prompt",
      ok: status.systemPromptBytes ? true : null,
      label: status.systemPromptBytes ? `${status.systemPromptBytes} bytes` : "Empty",
      evidence: "brain/prompts/system.md",
    },
  ];

  return (
    <>
      <Nav current="brain" />
      <main className="mx-auto max-w-7xl px-4 pt-28 pb-16 sm:px-6">
        <Reveal>
          <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">§7 · Memory contract</p>
          <h1 className="mt-4 text-5xl font-medium tracking-tight text-ink sm:text-6xl">
            Brain. <span className="font-serif text-[1.1em] italic text-accent-hi">Write like others will read.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-soft">
            The shared, namespaced memory of the fleet. Reads are logged, writes are versioned, and an agent can only touch the
            namespaces its manifest declares.{" "}
            {persistent ? "" : "Today the brain holds no records: the store is built, but nothing runs it against a file yet."}
          </p>
        </Reveal>

        <BrainView agents={agents} spaces={spaces} />

        <section className="mt-12" aria-label="Build status">
          <h2 className="text-2xl font-medium text-ink">Build status</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <tbody>
                {parts.map((p) => (
                  <tr key={p.part} className="border-t border-line">
                    <td className="py-3 pr-4 text-ink">{p.part}</td>
                    <td className="py-3 pr-4">
                      <State ok={p.ok} label={p.label} />
                    </td>
                    <td className="py-3 text-xs text-mute">{p.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
      <Footer current="brain" />
    </>
  );
}
