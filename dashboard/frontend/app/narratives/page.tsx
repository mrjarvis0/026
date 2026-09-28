import type { Metadata } from "next";
import { Footer, Nav } from "@/components/Nav";
import { NarrativesView } from "@/components/NarrativesView";
import { Reveal } from "@/components/Reveal";
import { loadFleet } from "@/lib/fleet";
import { loadNarratives } from "@/lib/narratives";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "narratives — 026" };

const STALE_HOURS = 24;

export default async function NarrativesPage() {
  const [{ narratives, items, lastScan }, fleet] = await Promise.all([loadNarratives(), loadFleet()]);
  const a002 = fleet.find((a) => a.id === "A002");
  const stale = !lastScan || lastScan.hoursAgo > STALE_HOURS;

  return (
    <>
      <Nav current="narratives" />
      <main className="mx-auto max-w-7xl px-4 pt-28 pb-16 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-[1.5fr_1fr] lg:items-end">
          <Reveal>
            <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">
              A002 · News Intelligence
            </p>
            <h1 className="mt-4 text-5xl font-medium tracking-tight text-ink sm:text-6xl">
              Narratives.{" "}
              <span className="font-serif text-[1.1em] italic text-accent-hi">What holds up.</span>
            </h1>
            <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-soft">
              Every story A002 is tracking, sorted by topic and graded on a seven-step evidence
              scale — never a binary fake or real. Truth, hype and coordination are three separate
              scores, and none of them is averaged into another.
            </p>
          </Reveal>

          <Reveal delay={0.1} className="frame p-5">
            <dl className="grid grid-cols-3 gap-4">
              <div>
                <dt className="text-[11px] text-mute">Narratives</dt>
                <dd className="mt-1 text-2xl font-semibold text-ink">{narratives.length}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-mute">News items</dt>
                <dd className="mt-1 text-2xl font-semibold text-ink">{items}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-mute">Last scan</dt>
                <dd className="mt-1 text-sm text-ink">{lastScan?.at ?? "never"}</dd>
              </div>
            </dl>
            <p className="mt-4 flex items-start gap-2 border-t border-line pt-3 text-xs leading-relaxed text-mute">
              {stale ? (
                <>
                  <svg viewBox="0 0 16 16" className="mt-px size-3.5 shrink-0 text-warning" fill="currentColor" aria-label="Warning">
                    <path d="M8 1.5 15 14H1L8 1.5Zm-.75 5v4h1.5v-4h-1.5Zm0 5v1.5h1.5V11.5h-1.5Z" />
                  </svg>
                  <span>
                    Data is older than {STALE_HOURS}h. Refresh with{" "}
                    <code className="font-pixel text-[10px] text-soft">python -m agents.A002_News_Intelligence.cli scan</code>
                  </span>
                </>
              ) : (
                <span>
                  Fresh — scanned {Math.max(1, Math.round(lastScan!.hoursAgo))}h ago, {lastScan!.stored} new items stored.
                </span>
              )}
            </p>
          </Reveal>
        </div>

        {a002 && (
          <Reveal className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-mute">
            <span className="text-soft">Detector maturity</span>
            {a002.detectors.map((d) => (
              <span key={d.id} className="flex items-center gap-1.5">
                <span className="font-pixel text-[10px] text-ink">{d.id}</span>
                <span className={d.maturity === "validated" ? "text-good" : "text-warning"}>{d.maturity}</span>
              </span>
            ))}
            <span>
              — until backtested, treat verdicts as graded evidence, not truth. Topics come from A002&apos;s
              category classifier (rules + ML).
            </span>
          </Reveal>
        )}

        <NarrativesView narratives={narratives} />
      </main>
      <Footer current="narratives" />
    </>
  );
}
