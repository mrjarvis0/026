"""FastAPI app: REST API + WebSocket + serves the dashboard."""
import asyncio
import contextlib
import logging

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.bot import bot
from backend.data import collector, database as db
from backend.strategy import engine as strategy_engine
from backend.trading import performance
from backend.trading.paper_engine import PaperEngine
from backend.trading.real_engine import RealEngine, RealTradingLocked
from backend.safety import circuit_breaker

log = logging.getLogger("trading.api")

# Upper bounds for user-supplied result limits (DoS protection).
MAX_LIMIT = 1000

# Host/Origin allowlist for DNS-rebinding + CSRF protection. This app has no
# auth by design (single-user localhost tool), so we must ensure requests are
# actually addressed to and originate from the local dashboard.
_hosts = {"127.0.0.1", "localhost",
          f"127.0.0.1:{config.PORT}", f"localhost:{config.PORT}"}
_origins = {f"http://127.0.0.1:{config.PORT}", f"http://localhost:{config.PORT}"}
if config.HOST not in ("127.0.0.1", "localhost", "0.0.0.0"):
    _hosts |= {config.HOST, f"{config.HOST}:{config.PORT}"}
    _origins |= {f"http://{config.HOST}:{config.PORT}"}
for _h in config.TRUSTED_HOSTS:
    _hosts.add(_h.lower())
    _origins.add(f"http://{_h.lower()}")
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _safe_error(exc: Exception, fallback: str) -> str:
    """Log the real error server-side; return a generic message to the client."""
    log.warning("%s: %s", fallback, exc)
    return fallback


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    task = asyncio.create_task(bot.run_forever())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="T01 Smart Binance Intelligence", lifespan=lifespan)


@app.middleware("http")
async def security_guard(request: Request, call_next):
    # DNS-rebinding protection: only serve requests addressed to a known host.
    host = (request.headers.get("host") or "").lower()
    if host and host not in _hosts:
        return PlainTextResponse("Forbidden host", status_code=403)
    # CSRF protection: state-changing requests must be same-origin. Browsers
    # always attach Origin on cross-site requests; non-browser clients (curl)
    # send none and are allowed.
    if request.method in UNSAFE_METHODS:
        origin = request.headers.get("origin")
        if origin is not None and origin.lower() not in _origins:
            return PlainTextResponse("Cross-origin request blocked", status_code=403)
    return await call_next(request)


# ---------------- REST API ----------------

@app.get("/api/status")
def status():
    allowed, msg = circuit_breaker.trading_allowed("paper")
    return {
        "running": bot.running,
        "symbol": bot.symbol,
        "timeframe": bot.timeframe,
        "last_price": bot.last_price,
        "last_signal": bot.last_signal,
        "emergency_stop": circuit_breaker.is_stopped(),
        "trading_allowed": allowed,
        "halt_reason": None if allowed else msg,
        "real_unlocked": performance.is_real_trading_unlocked(),
        "real_enabled": bot.real.enabled,
        "active_mode": bot.active_mode,
    }


@app.get("/api/symbols")
def symbols(quote: str = Query("USDT", max_length=10)):
    try:
        return {"symbols": collector.list_symbols(quote=quote)}
    except Exception as exc:
        return JSONResponse({"error": _safe_error(exc, "could not load symbols"),
                             "symbols": []}, status_code=200)


@app.post("/api/select")
def select_symbol(symbol: str, timeframe: str = config.DEFAULT_TIMEFRAME):
    bot.set_symbol(symbol, timeframe)
    return {"ok": True, "symbol": bot.symbol, "timeframe": bot.timeframe}


@app.post("/api/start")
def start_bot():
    bot.start()
    return {"ok": True, "running": True}


@app.post("/api/stop")
def stop_bot():
    bot.stop()
    return {"ok": True, "running": False}


@app.get("/api/metrics")
def metrics(mode: str = "paper"):
    return performance.compute_metrics(mode)


@app.get("/api/positions")
def positions(mode: str = "paper"):
    return {"positions": db.get_open_trades(mode=mode)}


@app.get("/api/trades")
def trades(mode: str = "paper", limit: int = Query(100, ge=1, le=MAX_LIMIT)):
    return {"trades": db.get_all_trades(mode=mode, limit=limit)}


@app.get("/api/equity")
def equity(mode: str = "paper"):
    return {"curve": db.get_equity_curve(mode=mode)}


@app.get("/api/indicators")
def indicators_snapshot():
    return {
        "symbol": bot.symbol,
        "indicators": bot.last_indicators,
        "signal": bot.last_signal,
        "params": strategy_engine.load_params(),   # dict, matching the WS payload
    }


@app.get("/api/activity")
def activity(limit: int = Query(60, ge=1, le=500)):
    return {"activity": list(bot.activity)[-limit:]}


@app.get("/api/orderbook")
def orderbook(symbol: str | None = Query(None, max_length=30),
              limit: int = Query(12, ge=1, le=100)):
    sym = symbol or bot.symbol
    try:
        return {"symbol": sym, **collector.fetch_order_book(sym, limit)}
    except Exception as exc:
        return JSONResponse({"error": _safe_error(exc, "could not load order book"),
                             "bids": [], "asks": []}, status_code=200)


@app.get("/api/balance")
def balance():
    p = PaperEngine()
    return {"paper_balance": p.balance, "start_balance": config.PAPER_START_BALANCE}


@app.get("/api/candles")
def candles(symbol: str | None = Query(None, max_length=30),
            timeframe: str | None = Query(None, max_length=5),
            limit: int = Query(100, ge=1, le=MAX_LIMIT)):
    sym = symbol or bot.symbol
    tf = timeframe or bot.timeframe
    try:
        data = collector.fetch_ohlcv(sym, tf, limit)
        return {"symbol": sym, "timeframe": tf, "candles": data}
    except Exception as exc:
        return JSONResponse({"error": _safe_error(exc, "could not load candles"),
                             "candles": []}, status_code=200)


# ---------------- Safety ----------------

@app.post("/api/emergency-stop")
def emergency_stop():
    circuit_breaker.emergency_stop()
    bot.stop()
    return {"ok": True, "stopped": True}


@app.post("/api/resume")
def resume():
    circuit_breaker.resume()
    return {"ok": True, "stopped": False}


@app.post("/api/reset-paper")
def reset_paper():
    # Reset the bot's LIVE engine instance, not a throwaway one — otherwise the
    # bot's in-memory balance overwrites the reset on its next save.
    bot.paper.reset()
    return {"ok": True, "balance": config.PAPER_START_BALANCE}


# ---------------- Real trading (guarded) ----------------

@app.post("/api/real/enable")
def enable_real():
    try:
        RealEngine().enable()
        return {"ok": True, "real_enabled": True}
    except RealTradingLocked as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=403)


@app.post("/api/real/disable")
def disable_real():
    RealEngine().disable()
    return {"ok": True, "real_enabled": False}


# ---------------- WebSocket ----------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    # Reject cross-origin WebSocket upgrades (defense against a malicious page
    # opening ws://127.0.0.1:8000/ws to read the live data stream).
    origin = ws.headers.get("origin")
    if origin is not None and origin.lower() not in _origins:
        await ws.close(code=1008)
        return
    await ws.accept()
    q = bot.subscribe()
    try:
        # send an initial snapshot
        await ws.send_json({"type": "status", **status()})
        while True:
            event = await q.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        bot.unsubscribe(q)


# ---------------- Static frontend ----------------

LANDING_DIR = config.FRONTEND_DIR / "landing"

app.mount("/static", StaticFiles(directory=str(config.FRONTEND_DIR)), name="static")
app.mount("/landing", StaticFiles(directory=str(LANDING_DIR)), name="landing")


@app.get("/")
def index():
    """Product landing page (front door)."""
    return FileResponse(str(LANDING_DIR / "index.html"))


@app.get("/terminal")
def terminal():
    """The T01 trading terminal dashboard."""
    return FileResponse(str(config.FRONTEND_DIR / "index.html"))
