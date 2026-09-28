"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useReducedMotion } from "motion/react";
import type { Module } from "@/lib/orchestrator";

const OrchestratorCore = dynamic(() => import("./OrchestratorCore"), { ssr: false });

const kb = (b: number) => (b >= 1024 ? `${(b / 1024).toFixed(1)} KB` : `${b} B`);

export function OrchestratorAnatomy({ modules }: { modules: Module[] }) {
  const still = !!useReducedMotion();
  const [selected, setSelected] = useState<string | null>(null);
  const picked = modules.find((m) => m.name === selected);

  return (
    <div className="grid gap-4 lg:grid-cols-[1.35fr_1fr]">
      <div className="frame relative h-[420px] overflow-hidden bg-panel/40 sm:h-[460px]">
        <OrchestratorCore
          modules={modules.map((m) => ({ name: m.name, bytes: m.bytes, files: m.files.length, tests: m.tests }))}
          selected={selected}
          onPick={(n) => setSelected((s) => (s === n ? null : n))}
          still={still}
        />
        <ul className="pointer-events-none absolute top-4 left-5 space-y-1 text-[11px] text-mute">
          <li className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">orchestrator/</li>
          <li>solid = has code (size ∝ code) · wireframe = empty</li>
          <li>packets flow only to built modules</li>
        </ul>
      </div>

      <div className="frame p-5">
        {picked ? (
          <>
            <div className="flex items-center justify-between">
              <h3 className="font-pixel text-sm text-ink">{picked.name}/</h3>
              <button type="button" onClick={() => setSelected(null)} className="text-xs text-mute hover:text-ink">
                all modules
              </button>
            </div>
            <p className="mt-1 text-xs text-mute">
              {picked.files.length} source file{picked.files.length === 1 ? "" : "s"} · {kb(picked.bytes)} · {picked.tests} test file
              {picked.tests === 1 ? "" : "s"}
            </p>
            {picked.files.length ? (
              <ul className="mt-4 space-y-1.5">
                {picked.files.map((f) => (
                  <li key={f.path} className="flex justify-between gap-3 text-xs">
                    <code className="truncate font-pixel text-[10px] text-soft">{f.path}</code>
                    <span className="shrink-0 text-mute tabular-nums">{kb(f.bytes)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-mute">Empty — this part of the orchestrator is not built yet.</p>
            )}
          </>
        ) : (
          <>
            <h3 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Modules</h3>
            <ul className="mt-4 space-y-2">
              {modules.map((m) => (
                <li key={m.name}>
                  <button
                    type="button"
                    onClick={() => setSelected(m.name)}
                    className="flex w-full items-center justify-between gap-3 text-left text-sm hover:text-ink"
                  >
                    <span className={`font-pixel text-xs ${m.bytes ? "text-accent-hi" : "text-mute"}`}>{m.name}/</span>
                    <span className="text-xs text-mute">{m.bytes ? `${m.files.length} files · ${kb(m.bytes)}` : "empty"}</span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
