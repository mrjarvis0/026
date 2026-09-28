"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "motion/react";

const STAGES = [
  ["sensors", "Watch the world — chains, feeds, APIs and MCP servers."],
  ["ingestion", "Pull raw records in; deduplicate; survive reorgs."],
  ["validation", "Reject what cannot be trusted; tag every record with its source."],
  ["normalization", "One shape for every record, timestamped and comparable."],
  ["store", "Raw and processed, versioned — nothing overwritten silently."],
  ["skills", "Reusable capabilities built over the store."],
  ["intelligence", "Detectors and analyzers, each under a measured confidence ceiling."],
  ["decision", "Report the deviation with its provenance — or say it cannot be determined."],
] as const;

const PLATFORM = [
  ["orchestrator", "plans, routes, fuses"],
  ["sentinel", "trust, invariants, execution gate"],
  ["brain", "shared, namespaced memory"],
  ["operator-io", "you — approvals and traces"],
] as const;

export function Pipeline() {
  const ref = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  useMotionValueEvent(scrollYProgress, "change", (v) =>
    setActive(Math.min(STAGES.length - 1, Math.max(0, Math.floor(v * STAGES.length)))),
  );

  return (
    <section id="architecture" ref={ref} className="relative h-[520vh]">
      <div className="sticky top-0 flex h-svh items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-7xl items-center gap-12 px-4 sm:px-6 md:grid-cols-[1fr_1fr]">
          <div>
            <p className="font-pixel text-[11px] uppercase tracking-[0.3em] text-accent">
              §1 · Anatomy of an agent
            </p>
            <h2 className="mt-4 text-4xl font-medium tracking-tight text-ink sm:text-5xl">
              One vertical pipeline.{" "}
              <span className="font-serif text-[1.1em] italic text-accent-hi">Owned end to end.</span>
            </h2>
            <ol className="mt-8 space-y-1">
              {STAGES.map(([name, desc], i) => (
                <li key={name} className="border-l border-line pl-4">
                  <div
                    className={`flex items-baseline gap-3 py-1 transition-colors duration-300 ${i === active ? "text-ink" : i < active ? "text-soft" : "text-mute/70"}`}
                  >
                    <span className="font-pixel text-[10px] text-mute">0{i + 1}</span>
                    <span className="font-pixel text-sm">{name}</span>
                  </div>
                  <AnimatePresence initial={false}>
                    {i === active && (
                      <motion.p
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="overflow-hidden pb-2 text-sm leading-relaxed text-soft"
                      >
                        {desc}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </li>
              ))}
            </ol>
            <p className="mt-8 max-w-md text-sm leading-relaxed text-mute">
              The platform surrounds this pipeline; it never reaches inside it.
            </p>
            <ul className="mt-4 grid grid-cols-2 gap-2">
              {PLATFORM.map(([name, role]) => (
                <li key={name} className="frame px-3 py-2">
                  <p className="font-pixel text-[11px] text-accent-hi">{name}</p>
                  <p className="mt-0.5 text-[11px] text-mute">{role}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="hidden h-[560px] items-center justify-center md:flex" aria-hidden>
            <div
              className="relative h-[210px] w-[210px]"
              style={{ transformStyle: "preserve-3d", transform: "rotateX(58deg) rotateZ(-42deg)" }}
            >
              {STAGES.map(([name], i) => {
                const lit = i <= active;
                return (
                  <div
                    key={name}
                    className="absolute inset-0 flex items-end justify-start border p-3 transition-all duration-500"
                    style={{
                      transform: `translateZ(${i * 34 + (i === active ? 14 : 0)}px)`,
                      borderColor: lit ? "rgb(95 184 234 / 0.7)" : "rgb(255 255 255 / 0.1)",
                      background: lit
                        ? `rgb(95 184 234 / ${i === active ? 0.22 : 0.08})`
                        : "rgb(12 14 18 / 0.55)",
                      boxShadow: i === active ? "0 0 60px rgb(95 184 234 / 0.35)" : "none",
                    }}
                  >
                    <span
                      className={`font-pixel text-[11px] ${lit ? "text-accent-hi" : "text-mute"}`}
                    >
                      0{i + 1} {name}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
