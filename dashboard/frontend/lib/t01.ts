// Server-only client for T01's own FastAPI service. T01 rejects cross-origin browser POSTs
// (CSRF guard) and unknown Host headers, so the dashboard talks to it from the server.
const BASE = process.env.T01_URL ?? "http://127.0.0.1:8000";

export const T01_START =
  "python -m uvicorn backend.main:app --app-dir agents/T01_Smart_Binance_Intelligence --host 127.0.0.1 --port 8000";
export const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];
export const SYMBOL_RE = /^[A-Z0-9]{2,15}\/[A-Z0-9]{2,10}$/;
export const REAL_CONFIRM = "ENABLE REAL MONEY";

export async function t01(path: string, method: "GET" | "POST" = "GET") {
  const res = await fetch(BASE + path, { method, cache: "no-store", signal: AbortSignal.timeout(10_000) });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}

// Everything the desk shows that lives inside T01 (no exchange round-trips), in one poll.
export async function snapshot() {
  // Any non-2xx (host guard, crash) means the snapshot is not trustworthy: fail the whole poll.
  const get = (p: string) =>
    t01(p).then((r) => {
      if (!r.ok) throw new Error(`${p} answered HTTP ${r.status}`);
      return r.body;
    });
  const [status, paper, real, paperPos, realPos, paperTrades, realTrades, paperEquity, indicators, activity, balance] =
    await Promise.all([
      get("/api/status"),
      get("/api/metrics?mode=paper"),
      get("/api/metrics?mode=real"),
      get("/api/positions?mode=paper"),
      get("/api/positions?mode=real"),
      get("/api/trades?mode=paper&limit=50"),
      get("/api/trades?mode=real&limit=50"),
      get("/api/equity?mode=paper"),
      get("/api/indicators"),
      get("/api/activity?limit=40"),
      get("/api/balance"),
    ]);
  return {
    status,
    metrics: { paper, real },
    positions: { paper: paperPos.positions ?? [], real: realPos.positions ?? [] },
    trades: { paper: paperTrades.trades ?? [], real: realTrades.trades ?? [] },
    equity: paperEquity.curve ?? [],
    indicators,
    activity: activity.activity ?? [],
    balance,
  };
}
