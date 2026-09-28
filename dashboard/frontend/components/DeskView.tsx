"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";
import type { Candle, Marker } from "./CandleScape";

const CandleScape = dynamic(() => import("./CandleScape"), { ssr: false });

type Trade = {
  id: number;
  mode: string;
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  stop_loss: number | null;
  take_profit: number | null;
  status: string;
  pnl: number | null;
  pnl_pct: number | null;
  entry_reason: string | null;
  exit_reason: string | null;
  entry_regime: string | null;
  opened_at: string;
  closed_at: string | null;
};
type Metrics = Record<string, number | boolean>;
type Snap = {
  status: {
    running: boolean;
    symbol: string;
    timeframe: string;
    last_price: number | null;
    last_signal: { action: string; confidence: number; reason: string; details?: { factors?: { name: string; score: number }[]; indicators?: Record<string, number | string> } } | null;
    emergency_stop: boolean;
    trading_allowed: boolean;
    halt_reason: string | null;
    real_unlocked: boolean;
    real_enabled: boolean;
    active_mode: string;
  };
  metrics: { paper: Metrics; real: Metrics };
  positions: { paper: Trade[]; real: Trade[] };
  trades: { paper: Trade[]; real: Trade[] };
  equity: { equity: number; ts: string }[];
  activity: { ts: string; level: string; message: string }[];
  balance: { paper_balance: number; start_balance: number };
};

const SNAP_MS = 5000;
const MARKET_MS = 15000;
const GOOD = "#0ca30c";
const BAD = "#d03b3b";
const num = (n: number | null | undefined, d = 2) =>
  n == null ? "—" : n.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });
const pnlColor = (n: number | null | undefined) => (n == null || n === 0 ? undefined : n > 0 ? GOOD : BAD);
const time = (iso: string | null) => (iso ? iso.slice(5, 16).replace("T", " ") : "—");

async function call(op: string, extra: Record<string, unknown> = {}) {
  const res = await fetch("/desk/t01", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ op, ...extra }),
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok && body.ok !== false, body };
}

export function DeskView({ timeframes, confirmPhrase, startCommand }: { timeframes: string[]; confirmPhrase: string; startCommand: string }) {
  const still = !!useReducedMotion();
  const [snap, setSnap] = useState<Snap | null>(null);
  const [down, setDown] = useState<string | null>(null);
  const [market, setMarket] = useState<{ candles: Candle[]; book: { bids: [number, number][]; asks: [number, number][] }; error?: string } | null>(null);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [symbol, setSymbol] = useState("");
  const [tf, setTf] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);
  const [mode, setMode] = useState<"paper" | "real">("paper");
  const [dialog, setDialog] = useState(false);
  const [typed, setTyped] = useState("");

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/desk/t01?op=snapshot", { cache: "no-store" });
      const body = await res.json();
      if (!res.ok || !body.up) throw new Error(body.error ?? `HTTP ${res.status}`);
      setSnap(body);
      setDown(null);
    } catch (e) {
      setDown((e as Error).message);
    }
  }, []);

  const s = snap?.status;
  const refreshMarket = useCallback(async () => {
    if (!s?.symbol || !s?.timeframe) return;
    const res = await fetch(`/desk/t01?op=market&symbol=${encodeURIComponent(s.symbol)}&timeframe=${s.timeframe}`, { cache: "no-store" });
    if (res.ok) setMarket(await res.json());
  }, [s?.symbol, s?.timeframe]);

  // Poll while the tab is visible; T01 keeps trading on its own either way.
  useEffect(() => {
    refresh();
    const id = setInterval(() => document.visibilityState === "visible" && refresh(), SNAP_MS);
    return () => clearInterval(id);
  }, [refresh]);
  useEffect(() => {
    refreshMarket();
    const id = setInterval(() => document.visibilityState === "visible" && refreshMarket(), MARKET_MS);
    return () => clearInterval(id);
  }, [refreshMarket]);
  useEffect(() => {
    if (!snap || symbols.length) return;
    fetch("/desk/t01?op=symbols").then((r) => r.json()).then((b) => setSymbols(b.symbols ?? [])).catch(() => {});
  }, [snap, symbols.length]);
  // Follow the instrument T01 is actually on, including changes made outside this tab.
  useEffect(() => {
    if (!s?.symbol) return;
    setSymbol(s.symbol);
    setTf(s.timeframe);
  }, [s?.symbol, s?.timeframe]);

  const act = async (op: string, label: string, extra: Record<string, unknown> = {}) => {
    setBusy(op);
    setNote(null);
    const r = await call(op, extra);
    setNote({ ok: r.ok, text: r.ok ? `${label}: done.` : `${label}: ${r.body.error ?? r.body.detail ?? "refused"}` });
    setBusy(null);
    await refresh();
    return r;
  };

  if (!snap) {
    return (
      <div className="frame mt-10 p-8">
        {down ? (
          <>
            <p className="text-sm text-warning">T01 is not running, so there is nothing to trade or show.</p>
            <p className="mt-3 text-xs text-soft">Start it from the repo root, then this page connects by itself:</p>
            <pre className="mt-2 overflow-x-auto border border-line bg-bg p-3 font-pixel text-[11px] text-ink">{startCommand}</pre>
            <p className="mt-3 text-[11px] text-mute">{down}</p>
          </>
        ) : (
          <p className="text-sm text-mute">Connecting to T01…</p>
        )}
      </div>
    );
  }

  const st = snap.status;
  const pm = snap.metrics.paper;
  const markers: Marker[] = snap.trades.paper
    .filter((t) => t.symbol === st.symbol)
    .flatMap((t) => [
      { id: t.id, kind: "entry" as const, ts: Date.parse(t.opened_at), price: t.entry_price, side: t.side, pnl: null },
      ...(t.closed_at && t.exit_price != null
        ? [{ id: t.id, kind: "exit" as const, ts: Date.parse(t.closed_at), price: t.exit_price, side: t.side, pnl: t.pnl }]
        : []),
    ]);
  const sig = st.last_signal;
  const trades = snap.trades[mode];
  const open = snap.positions[mode];
  const minTrades = Number(pm.min_trades);
  const threshold = Number(pm.unlock_threshold);
  const eq = snap.equity.slice(-200).map((p) => p.equity);
  const eqMin = Math.min(...eq);
  const eqMax = Math.max(...eq);

  return (
    <>
      {down && <p className="mt-6 text-xs text-warning">Lost contact with T01 — showing the last snapshot. {down}</p>}

      <dl className="mt-8 grid gap-px bg-line sm:grid-cols-3 lg:grid-cols-6">
        <Cell k="Bot" v={st.running ? "Running" : "Stopped"} dot={st.running ? GOOD : "#6b7280"} />
        <Cell k="Instrument" v={`${st.symbol}`} note={st.timeframe} />
        <Cell k="Last price" v={num(st.last_price)} />
        <Cell k="Signal" v={sig ? sig.action.toUpperCase() : "—"} note={sig ? `confidence ${(sig.confidence * 100).toFixed(0)}%` : ""} />
        <Cell
          k="Trading"
          v={st.emergency_stop ? "Emergency stop" : st.trading_allowed ? "Allowed" : "Halted"}
          dot={st.emergency_stop || !st.trading_allowed ? BAD : GOOD}
          note={st.halt_reason ?? ""}
        />
        <Cell k="Active mode" v={st.active_mode.toUpperCase()} dot={st.active_mode === "real" ? "#ec835a" : "#5fb8ea"} note={st.real_enabled ? "real mode enabled" : "paper — no real money"} />
      </dl>

      <section className="mt-4 grid gap-4 lg:grid-cols-[1.6fr_1fr]" aria-label="Market">
        <div className="frame relative h-[420px] overflow-hidden bg-panel/40 sm:h-[480px]">
          {market?.candles?.length ? (
            <CandleScape candles={market.candles} markers={markers} last={st.last_price} still={still} />
          ) : (
            <p className="p-6 text-sm text-mute">{market?.error ? `No candles: ${market.error}` : "Loading candles…"}</p>
          )}
          <ul className="pointer-events-none absolute top-4 left-5 space-y-1 text-[11px] text-mute">
            <li className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">
              {st.symbol} · {st.timeframe} · last {market?.candles?.length ?? 0} candles
            </li>
            <li>
              <span className="text-[#5fb8ea]">■ up</span> · <span className="text-[#e0803c]">■ down</span> · ◆ trade entry / exit · line = last price
            </li>
          </ul>
        </div>

        <div className="space-y-4">
          <div className="frame p-5">
            <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Controls</h2>
            <div className="mt-4 flex gap-2">
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                list="t01-symbols"
                aria-label="Symbol"
                spellCheck={false}
                className="min-w-0 flex-1 border border-line bg-transparent px-3 py-2 font-pixel text-xs text-ink focus:border-accent focus:outline-none"
              />
              <datalist id="t01-symbols">
                {symbols.map((x) => (
                  <option key={x} value={x} />
                ))}
              </datalist>
              <select value={tf} onChange={(e) => setTf(e.target.value)} aria-label="Timeframe" className="border border-line bg-panel px-2 text-sm text-ink">
                {timeframes.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
              <button
                type="button"
                disabled={!!busy || (symbol === st.symbol && tf === st.timeframe)}
                onClick={() => act("select", `Switch to ${symbol} ${tf}`, { symbol, timeframe: tf }).then(() => setMarket(null))}
                className="frame px-3 text-sm text-ink disabled:opacity-40"
              >
                Apply
              </button>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={!!busy}
                onClick={() => act(st.running ? "stop" : "start", st.running ? "Stop bot" : "Start bot")}
                className="bg-accent px-3 py-2 text-sm font-medium text-bg hover:bg-accent-hi disabled:opacity-50"
              >
                {st.running ? "Stop bot" : "Start bot"}
              </button>
              {st.emergency_stop ? (
                <button type="button" disabled={!!busy} onClick={() => act("resume", "Resume")} className="frame px-3 py-2 text-sm text-ink disabled:opacity-50">
                  Resume
                </button>
              ) : (
                <button
                  type="button"
                  disabled={!!busy}
                  onClick={() => act("emergency-stop", "Emergency stop")}
                  className="px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                  style={{ background: BAD }}
                >
                  Emergency stop
                </button>
              )}
              <button
                type="button"
                disabled={!!busy}
                onClick={() =>
                  window.confirm("Reset the paper wallet? Open paper positions close at entry (0 P&L) and the balance returns to the start value. Trade history is kept.") &&
                  act("reset-paper", "Reset paper wallet")
                }
                className="frame col-span-2 px-3 py-2 text-xs text-soft hover:text-ink disabled:opacity-50"
              >
                Reset paper wallet ({num(snap.balance.paper_balance)} → {num(snap.balance.start_balance)} USDT)
              </button>
            </div>
            <p aria-live="polite" className="mt-3 min-h-4 text-xs" style={{ color: note ? (note.ok ? GOOD : BAD) : undefined }}>
              {busy ? "Sending to T01…" : note?.text}
            </p>
          </div>

          <OrderBook book={market?.book} />
        </div>
      </section>

      <section className="mt-12 grid gap-4 lg:grid-cols-[1.4fr_1fr]" aria-label="Performance">
        <div className="frame p-5">
          <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Paper performance</h2>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat k="Closed trades" v={String(pm.total_trades)} note={`${pm.wins} won · ${pm.losses} lost`} />
            <Stat k="Accuracy" v={`${num(Number(pm.accuracy), 1)}%`} />
            <Stat k="Total P&L" v={`${num(Number(pm.total_pnl))} USDT`} color={pnlColor(Number(pm.total_pnl))} note={`ROI ${num(Number(pm.roi_pct))}%`} />
            <Stat k="Max drawdown" v={`${num(Number(pm.max_drawdown))}`} note={`Sharpe ${num(Number(pm.sharpe))} · PF ${num(Number(pm.profit_factor))}`} />
          </div>
          {eq.length > 1 && (
            <svg viewBox="0 0 100 30" preserveAspectRatio="none" className="mt-5 h-20 w-full" aria-label="Paper equity curve">
              <polyline
                fill="none"
                stroke="#5fb8ea"
                strokeWidth="0.6"
                vectorEffect="non-scaling-stroke"
                points={eq.map((v, i) => `${(i / (eq.length - 1)) * 100},${30 - ((v - eqMin) / (eqMax - eqMin || 1)) * 28 - 1}`).join(" ")}
              />
            </svg>
          )}
          <p className="text-[11px] text-mute">
            {eq.length ? `Paper equity · ${eq.length} points · ${num(eqMin)} – ${num(eqMax)} USDT` : "No paper equity recorded yet."}
          </p>
        </div>

        <div className="frame p-5">
          <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Real-money gate</h2>
          <p className="mt-2 text-xs leading-relaxed text-mute">
            T01 decides this, not the dashboard. Real orders need every line below — and they do not pass through the sentinel.
          </p>
          <Gauge label={`Paper trades ≥ ${minTrades}`} value={Number(pm.total_trades)} target={minTrades} suffix="" />
          <Gauge label={`Accuracy ≥ ${threshold}%`} value={Number(pm.accuracy)} target={threshold} suffix="%" />
          <ul className="mt-4 space-y-1.5 text-xs">
            <Check ok={st.real_unlocked} text={st.real_unlocked ? "Accuracy gate unlocked" : "Accuracy gate locked"} />
            <Check ok={null} text="Binance API credentials — checked by T01 when you enable" />
            <Check ok={st.real_enabled} text={st.real_enabled ? "Real mode enabled by operator" : "Real mode not enabled"} />
          </ul>
          <div className="mt-5">
            {st.real_enabled ? (
              <button type="button" disabled={!!busy} onClick={() => act("real-disable", "Disable real mode")} className="frame w-full px-3 py-2 text-sm text-ink">
                Disable real mode
              </button>
            ) : (
              <button
                type="button"
                disabled={!!busy}
                onClick={() => {
                  setTyped("");
                  setDialog(true);
                }}
                className="w-full border px-3 py-2 text-sm"
                style={{ borderColor: "#ec835a", color: "#ec835a" }}
              >
                Enable real mode…
              </button>
            )}
          </div>
        </div>
      </section>

      <section className="mt-12" aria-label="Trades">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-2xl font-medium text-ink">Positions &amp; trades</h2>
          <div className="flex border border-line text-xs">
            {(["paper", "real"] as const).map((m) => (
              <button key={m} type="button" onClick={() => setMode(m)} aria-pressed={mode === m} className={`px-3 py-1.5 ${mode === m ? "bg-white/[0.06] text-ink" : "text-soft"}`}>
                {m} ({snap.trades[m].length})
              </button>
            ))}
          </div>
        </div>
        <p className="mt-2 text-xs text-mute">
          {open.length} open {mode} position{open.length === 1 ? "" : "s"}
          {open.map((p) => ` · ${p.symbol} ${p.side} ${p.quantity} @ ${num(p.entry_price)}`).join("")}
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="text-[11px] text-mute">
              <tr>
                {["#", "Symbol", "Side", "Entry", "Exit", "Qty", "P&L", "Why in", "Why out", "Regime", "Opened", "Closed"].map((h) => (
                  <th key={h} className="py-2 pr-3 font-normal">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => (
                <tr key={t.id} className="border-t border-line text-xs">
                  <td className="py-2 pr-3 font-pixel text-[10px] text-mute">{t.id}</td>
                  <td className="py-2 pr-3 text-ink">{t.symbol}</td>
                  <td className="py-2 pr-3 text-soft">{t.side}</td>
                  <td className="py-2 pr-3 text-soft tabular-nums">{num(t.entry_price)}</td>
                  <td className="py-2 pr-3 text-soft tabular-nums">{num(t.exit_price)}</td>
                  <td className="py-2 pr-3 text-soft tabular-nums">{t.quantity}</td>
                  <td className="py-2 pr-3 tabular-nums" style={{ color: pnlColor(t.pnl) }}>
                    {t.status === "open" ? "open" : num(t.pnl)}
                  </td>
                  <td className="py-2 pr-3 text-mute">{t.entry_reason ?? "—"}</td>
                  <td className="py-2 pr-3 text-mute">{t.exit_reason ?? "—"}</td>
                  <td className="py-2 pr-3 text-mute">{t.entry_regime ?? "—"}</td>
                  <td className="py-2 pr-3 text-mute">{time(t.opened_at)}</td>
                  <td className="py-2 text-mute">{time(t.closed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!trades.length && <p className="frame mt-2 p-6 text-center text-sm text-mute">No {mode} trades yet.</p>}
        </div>
      </section>

      <section className="mt-12 grid gap-4 lg:grid-cols-2" aria-label="Signal and activity">
        <div className="frame p-5">
          <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Why the last signal</h2>
          <p className="mt-3 text-sm text-ink">{sig?.reason ?? "No signal yet."}</p>
          <ul className="mt-4 space-y-1.5">
            {(sig?.details?.factors ?? []).map((f) => (
              <li key={f.name} className="grid grid-cols-[8rem_1fr_3rem] items-center gap-2 text-xs">
                <span className="text-soft">{f.name.replaceAll("_", " ")}</span>
                <span className="relative h-2 bg-white/[0.05]">
                  <span
                    className="absolute top-0 h-full"
                    style={{
                      left: f.score >= 0 ? "50%" : `${50 + f.score * 25}%`,
                      width: `${Math.abs(f.score) * 25}%`,
                      background: f.score >= 0 ? "#5fb8ea" : "#e0803c",
                    }}
                  />
                </span>
                <span className="text-right text-mute tabular-nums">{f.score > 0 ? "+" : ""}{f.score}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4 grid grid-cols-3 gap-2 text-[11px] sm:grid-cols-4">
            {Object.entries(sig?.details?.indicators ?? {}).map(([k, v]) => (
              <p key={k}>
                <span className="text-mute">{k.replaceAll("_", " ")}</span>{" "}
                <span className="text-soft tabular-nums">{typeof v === "number" ? num(v) : v}</span>
              </p>
            ))}
          </div>
        </div>
        <div className="frame flex max-h-[26rem] flex-col p-5">
          <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Bot activity</h2>
          <ol className="mt-3 min-h-0 flex-1 space-y-1 overflow-y-auto font-pixel text-[10px]">
            {[...snap.activity].reverse().map((a, i) => (
              <li key={i} className="flex gap-2">
                <span className="shrink-0 text-mute">{a.ts.slice(11, 19)}</span>
                <span className={a.level === "error" ? "text-critical" : a.level === "trade" ? "text-accent-hi" : "text-soft"}>{a.message}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {dialog && (
        <div className="fixed inset-0 z-[60] grid place-items-center bg-bg/80 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Enable real mode">
          <div className="frame w-full max-w-md bg-panel p-6">
            <h2 className="text-lg text-ink">Enable real-money trading?</h2>
            <ul className="mt-4 space-y-2 text-sm leading-relaxed text-soft">
              <li>— T01 will place real orders on your Binance account with its own strategy.</li>
              <li>— These orders do not pass through the 026 sentinel gate.</li>
              <li>— T01 still refuses unless its accuracy gate is unlocked and API credentials are set.</li>
              <li>— You can disable it here or hit Emergency stop at any time.</li>
            </ul>
            <label className="mt-5 grid gap-1 text-xs text-mute">
              Type <span className="font-pixel text-[11px] text-ink">{confirmPhrase}</span> to confirm
              <input
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                autoFocus
                spellCheck={false}
                className="border border-line bg-transparent px-3 py-2 font-pixel text-xs text-ink focus:border-accent focus:outline-none"
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setDialog(false)} className="frame px-4 py-2 text-sm text-ink">
                Cancel
              </button>
              <button
                type="button"
                disabled={typed !== confirmPhrase || !!busy}
                onClick={async () => {
                  await act("real-enable", "Enable real mode", { confirm: typed });
                  setDialog(false);
                }}
                className="px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
                style={{ background: "#ec835a" }}
              >
                Enable real mode
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Cell({ k, v, note, dot }: { k: string; v: string; note?: string; dot?: string }) {
  return (
    <div className="bg-bg p-4">
      <dt className="text-[11px] text-mute">{k}</dt>
      <dd className="mt-1 flex items-center gap-2 text-lg font-semibold text-ink">
        {dot && <span className="size-2.5 shrink-0" style={{ background: dot }} />}
        <span className="truncate">{v}</span>
      </dd>
      {note && <p className="mt-0.5 truncate text-[11px] text-mute" title={note}>{note}</p>}
    </div>
  );
}

function Stat({ k, v, note, color }: { k: string; v: string; note?: string; color?: string }) {
  return (
    <div>
      <p className="text-[11px] text-mute">{k}</p>
      <p className="mt-1 text-xl font-semibold text-ink" style={{ color }}>
        {v}
      </p>
      {note && <p className="text-[11px] text-mute">{note}</p>}
    </div>
  );
}

function Gauge({ label, value, target, suffix }: { label: string; value: number; target: number; suffix: string }) {
  if (!Number.isFinite(value) || !Number.isFinite(target)) {
    return <p className="mt-4 text-xs text-mute">{label.replace("NaN", "?")} — T01 did not report this metric.</p>;
  }
  const pct = Math.min(100, (value / (target || 1)) * 100);
  return (
    <div className="mt-4">
      <div className="flex justify-between text-xs">
        <span className="text-soft">{label}</span>
        <span className="text-ink tabular-nums">
          {num(value, suffix ? 1 : 0)}
          {suffix} / {target}
          {suffix}
        </span>
      </div>
      <div className="mt-1 h-1.5 bg-white/[0.06]">
        <div className="h-full" style={{ width: `${pct}%`, background: pct >= 100 ? GOOD : "#fab219" }} />
      </div>
    </div>
  );
}

function Check({ ok, text }: { ok: boolean | null; text: string }) {
  return (
    <li className="flex items-center gap-2 text-soft">
      <span className="size-2.5 shrink-0" style={{ background: ok == null ? "#6b7280" : ok ? GOOD : "#fab219" }} />
      {text}
    </li>
  );
}

function OrderBook({ book }: { book?: { bids: [number, number][]; asks: [number, number][] } }) {
  if (!book) return <div className="frame p-5 text-sm text-mute">Loading order book…</div>;
  const max = Math.max(1e-9, ...book.bids.map((b) => b[1]), ...book.asks.map((a) => a[1]));
  const row = ([p, q]: [number, number], color: string) => (
    <li key={p} className="relative grid grid-cols-2 px-2 py-0.5 font-pixel text-[10px]">
      <span className="absolute inset-y-0 right-0 opacity-20" style={{ width: `${(q / max) * 100}%`, background: color }} />
      <span className="relative text-soft tabular-nums">{num(p, p < 10 ? 6 : 2)}</span>
      <span className="relative text-right text-mute tabular-nums">{q.toFixed(4)}</span>
    </li>
  );
  return (
    <div className="frame p-5">
      <h2 className="font-pixel text-[11px] uppercase tracking-[0.2em] text-soft">Order book</h2>
      <ol className="mt-3 flex flex-col-reverse">{book.asks.slice(0, 8).map((a) => row(a, "#e0803c"))}</ol>
      <div className="my-1 border-t border-line" />
      <ol>{book.bids.slice(0, 8).map((b) => row(b, "#5fb8ea"))}</ol>
    </div>
  );
}
