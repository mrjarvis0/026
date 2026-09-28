import { REAL_CONFIRM, SYMBOL_RE, TIMEFRAMES, snapshot, t01 } from "@/lib/t01";

export const dynamic = "force-dynamic";

const down = (e: unknown) => Response.json({ up: false, error: `T01 is not reachable (${(e as Error).message}).` }, { status: 503 });

// Reads: an explicit allowlist, never a passthrough.
export async function GET(req: Request) {
  const url = new URL(req.url);
  const op = url.searchParams.get("op");
  try {
    if (op === "snapshot") return Response.json({ up: true, ...(await snapshot()) });
    if (op === "market") {
      const symbol = url.searchParams.get("symbol") ?? "";
      const tf = url.searchParams.get("timeframe") ?? "";
      if (!SYMBOL_RE.test(symbol) || !TIMEFRAMES.includes(tf)) return Response.json({ error: "Bad symbol or timeframe." }, { status: 400 });
      const q = `symbol=${encodeURIComponent(symbol)}`;
      const [candles, book] = await Promise.all([
        t01(`/api/candles?${q}&timeframe=${tf}&limit=120`),
        t01(`/api/orderbook?${q}&limit=12`),
      ]);
      return Response.json({ candles: candles.body.candles ?? [], book: { bids: book.body.bids ?? [], asks: book.body.asks ?? [] }, error: candles.body.error ?? book.body.error });
    }
    if (op === "symbols") {
      const r = await t01("/api/symbols?quote=USDT");
      return Response.json({ symbols: (r.body.symbols ?? []).slice(0, 400), error: r.body.error });
    }
    return Response.json({ error: "Unknown op." }, { status: 400 });
  } catch (e) {
    return down(e);
  }
}

const CONTROLS: Record<string, string> = {
  start: "/api/start",
  stop: "/api/stop",
  "emergency-stop": "/api/emergency-stop",
  resume: "/api/resume",
  "reset-paper": "/api/reset-paper",
  "real-disable": "/api/real/disable",
};

// Controls. Real mode needs a typed confirmation here as well as in the UI; T01's own gate
// (accuracy + credentials) still decides whether it actually turns on.
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const op = String(body?.op ?? "");
  try {
    if (op === "select") {
      const symbol = String(body.symbol ?? "");
      const tf = String(body.timeframe ?? "");
      if (!SYMBOL_RE.test(symbol) || !TIMEFRAMES.includes(tf)) return Response.json({ error: "Bad symbol or timeframe." }, { status: 400 });
      const r = await t01(`/api/select?symbol=${encodeURIComponent(symbol)}&timeframe=${tf}`, "POST");
      return Response.json(r.body, { status: r.status });
    }
    if (op === "real-enable") {
      if (body.confirm !== REAL_CONFIRM) {
        return Response.json({ ok: false, error: `Type "${REAL_CONFIRM}" to confirm.` }, { status: 400 });
      }
      const r = await t01("/api/real/enable", "POST");
      return Response.json(r.body, { status: r.status });
    }
    const path = CONTROLS[op];
    if (!path) return Response.json({ error: "Unknown control." }, { status: 400 });
    const r = await t01(path, "POST");
    return Response.json(r.body, { status: r.status });
  } catch (e) {
    return down(e);
  }
}
