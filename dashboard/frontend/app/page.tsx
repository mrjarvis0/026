import Link from "next/link";
import { Hero } from "@/components/Hero";
import { Footer, Nav } from "@/components/Nav";
import { Pipeline } from "@/components/Pipeline";
import { Reveal } from "@/components/Reveal";
import { Voxel, type Cell } from "@/components/Voxel";
import { fleetStats, loadFleet, type Agent } from "@/lib/fleet";
import { MATURITY, MATURITY_COLOR, count, type Maturity } from "@/lib/maturity";

// Read the registry on every request: a stale snapshot would be a claim without evidence.
export const dynamic = "force-dynamic";

export default async function Home() {
  const agents = await loadFleet();
  const stats = fleetStats(agents);

  return (
    <>
      <Nav current="026" />
      <main>
        <Hero agents={agents} />
        <Laws />
        <Pipeline />
        <Fleet agents={agents} stats={stats} />
        <Correlation />
      </main>
      <Footer current="026" />
    </>
  );
}

function SectionHead({
  eyebrow,
  title,
  accent,
  children,
}: {
  eyebrow: string;
  title: string;
  accent: string;
  children?: React.ReactNode;
}) {
  return (
    <Reveal className="max-w-3xl">
      <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">{eyebrow}</p>
      <h2 className="mt-4 text-4xl font-medium tracking-tight text-ink sm:text-5xl">
        {title} <span className="font-serif text-[1.1em] italic text-accent-hi">{accent}</span>
      </h2>
      {children && <p className="mt-5 text-[15px] leading-relaxed text-soft">{children}</p>}
    </Reveal>
  );
}

const grid3 = (y: number, hl: [number, number] | null = null): Cell[] =>
  [0, 1, 2].flatMap((x) =>
    [0, 1, 2].map((z): Cell => [x, y, z, hl && hl[0] === x && hl[1] === z ? 1 : 0]),
  );

const LAWS: { title: string; body: string; cells: Cell[] }[] = [
  {
    title: "Evidence standard",
    body: "An agent asserts only what its evidence licenses.",
    cells: [...grid3(0), [1, 1, 1, 0], [1, 2, 1, 1]],
  },
  {
    title: "Maturity gates",
    body: "A detector may alert only when its error rate is measured.",
    cells: [0, 1].flatMap((z): Cell[] => [
      [0, 0, z, 0],
      [1, 0, z, 0],
      [1, 1, z, 0],
      [2, 0, z, 0],
      [2, 1, z, 0],
      [2, 2, z, 1],
    ]),
  },
  {
    title: "Coverage before absence",
    body: "A negative claim requires proof the window was observed.",
    cells: [
      [0, 0, 0, 0], [1, 0, 0, 0], [2, 0, 0, 0], [0, 1, 0, 0],
      [2, 1, 0, 0], [0, 2, 0, 0], [1, 2, 0, 0], [2, 2, 0, 1],
    ],
  },
  {
    title: "Provenance",
    body: "Every conclusion traces to a raw, sourced, timestamped record.",
    cells: [
      [0, 0, 0, 1], [1, 0, 0, 0], [1, 0, 1, 0], [2, 0, 1, 0],
      [2, 0, 2, 0], [2, 1, 2, 0], [2, 2, 2, 0],
    ],
  },
  {
    title: "Gated execution",
    body: "Real-money trading is off by default and fires only through the sentinel's gate.",
    cells: [
      [0, 0, 0, 0], [0, 1, 0, 0], [0, 2, 0, 0], [2, 0, 0, 0],
      [2, 1, 0, 0], [2, 2, 0, 0], [1, 2, 0, 0], [1, 0, 0, 1],
    ],
  },
  {
    title: "Downward-only imports",
    body: "Layer N imports only from the layers below it — mechanically checked.",
    cells: [
      ...grid3(0),
      [1, 1, 0, 0], [0, 1, 1, 0], [1, 1, 1, 0], [2, 1, 1, 0], [1, 1, 2, 0],
      [1, 2, 1, 1],
    ],
  },
];

function Laws() {
  return (
    <section id="laws" className="mx-auto max-w-7xl px-4 py-32 sm:px-6">
      <SectionHead eyebrow="§0 · The laws" title="Six laws." accent="No exceptions.">
        They are not style — they are the reason the system can be trusted. Every agent and every
        build session obeys them.
      </SectionHead>
      <div className="mt-16 grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-3">
        {LAWS.map((law, i) => (
          <Reveal key={law.title} delay={(i % 3) * 0.08} className="bg-bg">
            <article className="group relative flex h-full flex-col p-8 transition-colors hover:bg-white/[0.02]">
              <span className="font-pixel text-[10px] text-mute">0{i + 1}</span>
              <div className="my-6 self-center">
                <Voxel cells={law.cells} />
              </div>
              <h3 className="font-pixel text-sm text-ink">{law.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-soft">{law.body}</p>
            </article>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function MaturityChip({ status }: { status: Maturity }) {
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

function Stat({
  label,
  value,
  note,
  warning = false,
}: {
  label: string;
  value: string;
  note: string;
  warning?: boolean;
}) {
  return (
    <div className="frame p-5">
      <p className="text-[13px] text-soft">{label}</p>
      <p className="mt-2 text-4xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="mt-2 flex items-center gap-1.5 text-xs text-mute">
        {warning && (
          <svg viewBox="0 0 16 16" className="size-3.5 shrink-0 text-warning" fill="currentColor" aria-label="Warning">
            <path d="M8 1.5 15 14H1L8 1.5Zm-.75 5v4h1.5v-4h-1.5Zm0 5v1.5h1.5V11.5h-1.5Z" />
          </svg>
        )}
        {note}
      </p>
    </div>
  );
}

function Fleet({ agents, stats }: { agents: Agent[]; stats: ReturnType<typeof fleetStats> }) {
  return (
    <section id="fleet" className="mx-auto max-w-7xl px-4 py-32 sm:px-6">
      <SectionHead
        eyebrow="§3 · The fleet"
        title={`${stats.total} agents.`}
        accent={`${stats.registered} registered.`}
      >
        Read live from <code className="font-pixel text-[12px] text-ink">config/agents/registry.yaml</code>{" "}
        and each agent&apos;s manifest on every request. No number on this page is typed by hand.
      </SectionHead>

      <Reveal className="mt-14 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Stat
          label="Agents"
          value={String(stats.total)}
          note={`${stats.registered} registered · ${stats.planned} planned`}
        />
        <Stat
          label="Detectors"
          value={String(stats.detectors)}
          note={`declared across ${stats.registered} registered agents`}
        />
        <Stat
          label="Validated detectors"
          value={String(stats.validated)}
          note={stats.validated ? "measured error rate — may alert" : "none may alert until backtested"}
          warning={stats.validated === 0}
        />
        <Stat
          label="Kernel-wired"
          value={`${stats.kernelWired.length} of ${stats.registered}`}
          note={`on the shared bus: ${stats.kernelWired.join(" · ") || "none"}`}
        />
        <Stat label="Typed tools" value={String(stats.tools)} note="distinct tools across the fleet" />
        <Stat
          label="Execution-enabled"
          value={String(stats.execution.length)}
          note={`${stats.execution.join(" · ")} — behind the sentinel gate`}
        />
      </Reveal>

      <Reveal className="mt-14 flex flex-wrap items-center gap-x-6 gap-y-2">
        <span className="text-[13px] text-soft">Build maturity</span>
        {MATURITY.map((m) => (
          <span key={m} className="flex items-center gap-2">
            <MaturityChip status={m} />
            <span className="text-xs text-mute">{stats.byStatus[m]}</span>
          </span>
        ))}
      </Reveal>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
        {agents.map((a, i) => (
          <Reveal key={a.id} delay={(i % 5) * 0.04}>
            <Link
              href={`/agents?id=${a.id}`}
              className={`frame group block h-full p-4 transition hover:-translate-y-0.5 hover:border-line-strong ${a.registered ? "" : "border-dashed opacity-60 hover:opacity-100"}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-pixel text-sm text-accent-hi">{a.id}</span>
                <MaturityChip status={a.status} />
              </div>
              <h3 className="mt-3 text-[15px] font-medium text-ink">{a.name}</h3>
              <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-mute">
                {a.domain || "Spec only — not yet registered."}
              </p>
              {a.registered && (
                <>
                  <p className="mt-4 text-[11px] text-soft">
                    {count(a.tools.length, "tool")} · {count(a.detectors.length, "detector")} · trust{" "}
                    {a.trust}
                  </p>
                  {(a.kernelWired || a.execution) && (
                    <div className="mt-2 flex gap-2 font-pixel text-[8px] uppercase">
                      {a.kernelWired && <span className="border border-accent/40 px-1.5 py-0.5 text-accent">on the bus</span>}
                      {a.execution && <span className="border border-serious/50 px-1.5 py-0.5 text-serious">exec gated</span>}
                    </div>
                  )}
                </>
              )}
            </Link>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function Correlation() {
  const Arrow = () => <div className="flow-y mx-auto h-10 w-px lg:flow-x lg:h-px lg:w-full" aria-hidden />;
  return (
    <section id="correlation" className="mx-auto max-w-7xl px-4 py-32 sm:px-6">
      <SectionHead eyebrow="§4 · Cross-agent correlation" title="Answers that combine." accent="Never average.">
        Single agents answer single questions. The brain and the orchestrator let their answers meet —
        each half keeping its own provenance.
      </SectionHead>

      <Reveal className="mt-16">
        <p className="mb-4 font-pixel text-[9px] uppercase tracking-[0.2em] text-mute">
          Illustrative example from AGENTS.md §4 — not live data
        </p>
        <div className="grid items-center gap-0 lg:grid-cols-[1.1fr_56px_0.8fr_56px_1.1fr]">
          <div className="space-y-3">
            <div className="frame p-4">
              <p className="font-pixel text-[11px] text-accent-hi">A002 · news</p>
              <p className="mt-2 text-sm text-ink">Unverified exploit rumor on protocol X</p>
              <p className="mt-1 text-xs text-mute">coordination score 78 / 100</p>
            </div>
            <div className="frame p-4">
              <p className="font-pixel text-[11px] text-accent-hi">A001 · chain</p>
              <p className="mt-2 text-sm text-ink">Anomalous outflow from X&apos;s treasury</p>
              <p className="mt-1 text-xs text-mute">z = 7.1</p>
            </div>
          </div>
          <Arrow />
          <div>
            <div className="frame p-4 text-center">
              <p className="font-pixel text-[11px] text-ink">orchestrator</p>
              <p className="mt-1 text-xs text-mute">fuses</p>
            </div>
            <div className="flow-y mx-auto h-8 w-px" aria-hidden />
            <div className="frame p-4 text-center">
              <p className="font-pixel text-[11px] text-ink">sentinel</p>
              <p className="mt-1 text-xs text-mute">gates</p>
            </div>
          </div>
          <Arrow />
          <div className="frame border-accent/40 p-5">
            <p className="font-pixel text-[11px] text-accent-hi">Correlated finding</p>
            <ul className="mt-3 space-y-2 text-sm text-soft">
              <li>Confidence = the weakest input, not the mean.</li>
              <li>Two provenance chains, kept split.</li>
              <li>Disagreements recorded, never resolved away.</li>
            </ul>
            <p className="mt-4 flex items-center gap-1.5 text-xs text-mute">
              <svg viewBox="0 0 16 16" className="size-3.5 text-warning" fill="currentColor" aria-label="Held">
                <path d="M8 1.5 15 14H1L8 1.5Zm-.75 5v4h1.5v-4h-1.5Zm0 5v1.5h1.5V11.5h-1.5Z" />
              </svg>
              A hypothesis until each half clears its own maturity gate.
            </p>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
