"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useReducedMotion } from "motion/react";
import { BLOCK_STATE, type BlockState } from "@/lib/status";

const ChainHelix = dynamic(() => import("./ChainHelix"), { ssr: false });

export type OnBlock = {
  number: number;
  time: string;
  txs: number;
  state: BlockState;
  valueEth: number;
  gasPct: number | null;
  top: { hash: string; from: string; to: string | null; eth: number }[];
};
export type Flow = { entity: string; inCount: number; inEth: number; outCount: number; outEth: number; netEth: number };

const HASH = /^0x[0-9a-fA-F]{64}$/;
const ADDR = /^0x[0-9a-fA-F]{40}$/;
const short = (s: string) => `${s.slice(0, 6)}…${s.slice(-4)}`;
const fmt = (n: number, d = 2) => n.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });
const IN = "#5fb8ea";
const OUT = "#e0803c";

export function TxLink({ hash }: { hash: string }) {
  return HASH.test(hash) ? (
    <a href={`https://etherscan.io/tx/${hash}`} target="_blank" rel="noopener noreferrer" className="font-pixel text-[10px] text-accent hover:text-accent-hi">
      {short(hash)}
    </a>
  ) : (
    <span className="font-pixel text-[10px] text-mute">{short(hash)}</span>
  );
}

export function Addr({ a, labels }: { a: string | null; labels: Record<string, string> }) {
  if (!a) return <span className="text-mute">contract creation</span>;
  const name = labels[a];
  const text = name ? name : short(a);
  return ADDR.test(a) ? (
    <a
      href={`https://etherscan.io/address/${a}`}
      target="_blank"
      rel="noopener noreferrer"
      title={a}
      className={name ? "text-ink hover:text-accent-hi" : "font-pixel text-[10px] text-soft hover:text-ink"}
    >
      {text}
    </a>
  ) : (
    <span className="font-pixel text-[10px] text-soft">{text}</span>
  );
}

export function OnchainStage({ blocks, labels }: { blocks: OnBlock[]; labels: Record<string, string> }) {
  const still = !!useReducedMotion();
  const [picked, setPicked] = useState<number | null>(null);
  const b = blocks.find((x) => x.number === picked);
  const counts = (Object.keys(BLOCK_STATE) as BlockState[]).map((s) => [s, blocks.filter((x) => x.state === s).length] as const);

  return (
    <section className="mt-10 grid gap-4 lg:grid-cols-[1.35fr_1fr]" aria-label="Chain">
      <div className="frame relative h-[440px] overflow-hidden bg-panel/40 sm:h-[500px]">
        <ChainHelix
          blocks={blocks.map((x) => ({ number: x.number, txs: x.txs, state: x.state, valueEth: x.valueEth, time: x.time }))}
          selected={picked}
          onPick={(n) => setPicked((p) => (p === n ? null : n))}
          still={still}
        />
        <ul className="pointer-events-none absolute top-4 left-5 space-y-1 text-[11px] text-mute">
          <li className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">{blocks.length} blocks, in order</li>
          <li>height = transactions in the block</li>
          {counts.map(([s, n]) => (
            <li key={s} className="flex items-center gap-2">
              <span
                className={`size-2.5 ${s === "unfetched" ? "border border-mute" : ""}`}
                style={s === "unfetched" ? undefined : { background: BLOCK_STATE[s].color }}
              />
              {n} {BLOCK_STATE[s].label.split(" — ")[0]}
            </li>
          ))}
        </ul>
      </div>

      <div className="frame p-5">
        {b ? (
          <>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-pixel text-lg text-ink">#{b.number.toLocaleString("en-US")}</p>
                <p className="text-xs text-mute">{b.time.replace("T", " ").replace("+00:00", " UTC")}</p>
              </div>
              <button type="button" onClick={() => setPicked(null)} className="text-xs text-mute hover:text-ink">
                window
              </button>
            </div>
            <dl className="mt-4 grid grid-cols-3 gap-3 text-xs">
              <div>
                <dt className="text-mute">Txs</dt>
                <dd className="text-ink tabular-nums">{b.txs}</dd>
              </div>
              <div>
                <dt className="text-mute">ETH moved</dt>
                <dd className="text-ink tabular-nums">{fmt(b.valueEth)}</dd>
              </div>
              <div>
                <dt className="text-mute">Gas used</dt>
                <dd className="text-ink tabular-nums">{b.gasPct == null ? "—" : `${b.gasPct.toFixed(0)}%`}</dd>
              </div>
            </dl>
            <p className="mt-3 flex items-center gap-2 text-xs text-soft">
              <span
                className={`size-2.5 ${b.state === "unfetched" ? "border border-mute" : ""}`}
                style={b.state === "unfetched" ? undefined : { background: BLOCK_STATE[b.state].color }}
              />
              {BLOCK_STATE[b.state].label}
            </p>
            <p className="mt-5 text-[11px] text-mute">Largest ETH transfers in this block</p>
            <ul className="mt-2 space-y-2">
              {b.top.map((t) => (
                <li key={t.hash} className="text-xs">
                  <div className="flex justify-between gap-2">
                    <TxLink hash={t.hash} />
                    <span className="text-ink tabular-nums">{fmt(t.eth, 4)} ETH</span>
                  </div>
                  <p className="mt-0.5 truncate text-[11px] text-mute">
                    <Addr a={t.from} labels={labels} /> → <Addr a={t.to} labels={labels} />
                  </p>
                </li>
              ))}
              {!b.top.length && <li className="text-xs text-mute">No transactions stored for this block.</li>}
            </ul>
          </>
        ) : (
          <>
            <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">The window</h2>
            <p className="mt-3 text-sm leading-relaxed text-soft">
              Every block A001 stored, oldest at the bottom, each linked to its parent. Hollow blocks have their
              transactions but not their token-transfer logs — so nothing can be concluded about token activity inside them.
            </p>
            <p className="mt-4 text-xs text-mute">Drag to turn the chain · click a block to open it.</p>
          </>
        )}
      </div>
    </section>
  );
}

export function FlowChart({ flows }: { flows: Flow[] }) {
  const rows = [...flows].sort((a, b) => b.inEth + b.outEth - (a.inEth + a.outEth)).slice(0, 12);
  const max = Math.max(1e-9, ...rows.flatMap((r) => [r.inEth, r.outEth]));
  return (
    <div>
      <div className="grid grid-cols-[1fr_7rem_1fr] text-[11px] text-mute">
        <p className="text-right" style={{ color: OUT }}>
          ← withdrawals from exchange
        </p>
        <span />
        <p style={{ color: IN }}>deposits to exchange →</p>
      </div>
      <ul className="mt-2 space-y-1.5">
        {rows.map((r) => (
          <li key={r.entity} className="grid grid-cols-[1fr_7rem_1fr] items-center text-[11px]" title={`${r.entity}: ${r.inCount} deposits, ${r.outCount} withdrawals`}>
            <div className="flex items-center justify-end gap-2">
              <span className="text-soft tabular-nums">{r.outEth ? fmt(r.outEth, 1) : ""}</span>
              <span className="h-3" style={{ width: `${(r.outEth / max) * 100}%`, background: OUT, minWidth: r.outEth ? 2 : 0 }} />
            </div>
            <span className="truncate px-2 text-center text-ink">{r.entity}</span>
            <div className="flex items-center gap-2">
              <span className="h-3" style={{ width: `${(r.inEth / max) * 100}%`, background: IN, minWidth: r.inEth ? 2 : 0 }} />
              <span className="text-soft tabular-nums">{r.inEth ? fmt(r.inEth, 1) : ""}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
