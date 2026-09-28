import type { Metadata } from "next";
import { DeskView } from "@/components/DeskView";
import { Footer, Nav } from "@/components/Nav";
import { Reveal } from "@/components/Reveal";
import { REAL_CONFIRM, T01_START, TIMEFRAMES } from "@/lib/t01";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "desk — 026" };

export default function DeskPage() {
  return (
    <>
      <Nav current="desk" />
      <main className="mx-auto max-w-7xl px-4 pt-28 pb-16 sm:px-6">
        <Reveal>
          <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">T01 · Smart Binance Intelligence</p>
          <h1 className="mt-4 text-5xl font-medium tracking-tight text-ink sm:text-6xl">
            Desk. <span className="font-serif text-[1.1em] italic text-accent-hi">Paper first. Real only through the gate.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-soft">
            T01 trades on its own strategy; this desk runs it, watches it and stops it. Every figure is live from T01&apos;s service.
            Real money stays locked until T01&apos;s own accuracy gate opens and you enable it.
          </p>
        </Reveal>
        <DeskView timeframes={TIMEFRAMES} confirmPhrase={REAL_CONFIRM} startCommand={T01_START} />
      </main>
      <Footer current="desk" />
    </>
  );
}
