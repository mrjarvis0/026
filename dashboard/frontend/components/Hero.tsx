"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import type { Agent } from "@/lib/fleet";
import { MATURITY_COLOR, count } from "@/lib/maturity";

const HeroScene = dynamic(() => import("./HeroScene"), { ssr: false });

export function Hero({ agents }: { agents: Agent[] }) {
  const ref = useRef<HTMLElement>(null);
  const still = !!useReducedMotion();
  const [hovered, setHovered] = useState<Agent | null>(null);
  const router = useRouter();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], [0, still ? 0 : 140]);
  const opacity = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  return (
    <section ref={ref} className="relative h-svh min-h-[680px] overflow-hidden">
      <div className="absolute inset-0">
        <HeroScene
          agents={agents}
          onHover={setHovered}
          onOpen={(a) => router.push(`/agents?id=${a.id}`)}
          still={still}
        />
      </div>
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,var(--color-bg)_0%,rgb(6_7_10/0.88)_38%,transparent_68%)] max-md:bg-[linear-gradient(0deg,var(--color-bg)_30%,rgb(6_7_10/0.7)_60%,transparent_85%)]" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-bg to-transparent" />

      <motion.div
        style={{ y, opacity }}
        className="pointer-events-none relative mx-auto flex h-full max-w-7xl flex-col justify-end px-4 pb-40 sm:px-6 md:justify-center md:pb-0"
      >
        <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">
          Intelligence Engine OS
        </p>
        <h1 className="mt-4 font-pixel text-[clamp(6.5rem,22vw,15rem)] leading-[0.78] tracking-tight text-ink">
          026
        </h1>
        <p className="mt-8 max-w-xl text-2xl leading-snug text-ink sm:text-3xl">
          A fleet of evidence-grade agents.
          <span className="block font-serif text-[1.15em] italic text-accent-hi">One brain. One gate.</span>
        </p>
        <p className="mt-4 max-w-md text-[15px] leading-relaxed text-soft">
          Every agent owns its pipeline from sensor to decision. Every claim traces to a sourced,
          timestamped record. Nothing trades without the sentinel&apos;s gate.
        </p>
        <div className="pointer-events-auto mt-9 flex flex-wrap gap-3">
          <a
            href="#fleet"
            className="bg-accent px-5 py-3 text-sm font-medium text-bg transition hover:bg-accent-hi"
          >
            Meet the fleet
          </a>
          <a
            href="#laws"
            className="frame px-5 py-3 text-sm text-ink transition hover:border-line-strong"
          >
            Read the laws
          </a>
        </div>
      </motion.div>

      <AnimatePresence>
        {hovered && (
          <motion.aside
            key={hovered.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.2 }}
            className="frame pointer-events-none absolute right-4 top-20 w-72 bg-panel/90 p-4 backdrop-blur-md sm:right-6"
          >
            <div className="flex items-center justify-between">
              <span className="font-pixel text-sm text-accent-hi">{hovered.id}</span>
              <span className="flex items-center gap-1.5 font-pixel text-[10px] uppercase text-soft">
                <span className="size-2" style={{ background: MATURITY_COLOR[hovered.status] }} />
                {hovered.status}
              </span>
            </div>
            <p className="mt-2 text-[15px] font-medium text-ink">{hovered.name}</p>
            <p className="mt-1 text-xs leading-relaxed text-mute">
              {hovered.domain || "Spec only — not yet registered in the fleet."}
            </p>
            {hovered.registered && (
              <p className="mt-3 text-xs text-soft">
                {count(hovered.tools.length, "tool")} · {count(hovered.detectors.length, "detector")} ·
                trust {hovered.trust}
                {hovered.kernelWired && <span className="text-accent"> · on the bus</span>}
                {hovered.execution && <span className="text-serious"> · execution-gated</span>}
              </p>
            )}
            <p className="mt-3 font-pixel text-[9px] uppercase tracking-wider text-accent">Click to open its contract</p>
          </motion.aside>
        )}
      </AnimatePresence>

      <div className="absolute inset-x-0 bottom-0 mx-auto flex max-w-7xl items-end justify-between gap-6 px-4 pb-6 sm:px-6">
        <ul className="flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-mute">
          <li className="flex items-center gap-2">
            <span className="h-px w-5 bg-accent" /> on the shared bus (live pulses)
          </li>
          <li className="flex items-center gap-2">
            <span className="h-px w-5 border-t border-dashed border-accent/60" /> declared, not yet wired
          </li>
          <li className="flex items-center gap-2">
            <span className="size-2.5 border border-mute" /> outer ring: planned
          </li>
          <li className="flex items-center gap-2">
            <span className="size-2.5 rounded-full border border-serious" /> execution-gated
          </li>
          <li className="hidden sm:block">Hover a node to inspect it</li>
        </ul>
        <span className="hidden font-pixel text-[10px] uppercase tracking-[0.3em] text-mute md:block">
          Scroll
        </span>
      </div>
    </section>
  );
}
