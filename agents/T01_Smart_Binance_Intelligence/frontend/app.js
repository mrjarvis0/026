"use strict";
/* T01 trading terminal — vanilla JS, no deps. Talks to the FastAPI backend
   over REST (fetch) + a live WebSocket at /ws. */

const $ = (id) => document.getElementById(id);
const fmt = (n, d = 2) =>
  (n === null || n === undefined || Number.isNaN(Number(n)))
    ? "—" : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });

const state = {
  symbol: null, timeframe: "5m",
  candles: [],          // [[ts,o,h,l,c,v],...]
  equity: [],           // [{balance,equity,ts}]
  lastPrice: null,
  mode: "paper",        // active engine: "paper" | "real"
};

/* ---------------- REST helpers ---------------- */
async function apiGet(path) {
  const r = await fetch(path, { headers: { "Accept": "application/json" } });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}
async function apiPost(path) {
  // POST endpoints take query params; same-origin so the CSRF Origin check passes.
  const r = await fetch(path, { method: "POST", headers: { "Accept": "application/json" } });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

/* ---------------- rendering ---------------- */
function setConn(ok) {
  const d = $("conn-dot");
  d.classList.toggle("on", ok);
  d.classList.toggle("off", !ok);
}

function renderStatus(s) {
  if (s.active_mode && s.active_mode !== state.mode) {
    state.mode = s.active_mode;
    loadEquity().catch(() => {});
    apiGet(`/api/metrics?mode=${state.mode}`).then(renderMetrics).catch(() => {});
    apiGet(`/api/positions?mode=${state.mode}`).then(r => renderPositions(r.positions)).catch(() => {});
  }
  const live = $("live-badge"); if (live) live.hidden = state.mode !== "real";
  $("running-chip").textContent = s.running ? "running" : "idle";
  $("running-chip").classList.toggle("on", !!s.running);
  const banner = $("halt-banner");
  if (s.trading_allowed === false) {
    banner.hidden = false;
    banner.textContent = "⛔ " + (s.halt_reason || "Trading halted");
  } else banner.hidden = true;
  $("btn-resume").hidden = !s.emergency_stop;
  if (s.last_price != null) setPrice(s.last_price);
  if (s.last_signal) renderSignal(s.last_signal);
}

function setPrice(p) {
  state.lastPrice = p;
  $("last-price").textContent = fmt(p, priceDecimals(p));
}
function priceDecimals(p) { p = Math.abs(Number(p) || 0); return p >= 100 ? 2 : p >= 1 ? 4 : 6; }

function renderTicker(t) {
  if (!t) return;
  const chip = $("price-change");
  const c = Number(t.change_pct);
  if (!Number.isNaN(c)) {
    chip.textContent = (c >= 0 ? "+" : "") + fmt(c, 2) + "%";
    chip.className = "chip " + (c >= 0 ? "up" : "down");
  }
}

function renderSignal(sig) {
  if (!sig) return;
  const action = (sig.action || "hold").toLowerCase();
  const el = $("signal-action");
  el.textContent = action.toUpperCase();
  el.className = "signal-action " + action;
  const conf = Math.max(0, Math.min(1, Number(sig.confidence) || 0));
  $("conf-bar").style.width = (conf * 100).toFixed(0) + "%";
  $("signal-reason").textContent = sig.reason || "";
  const factors = (sig.details && sig.details.factors) || [];
  $("factors").innerHTML = factors.map(f =>
    `<li class="${f.score >= 0 ? "pos" : "neg"}">${f.name} ${f.score >= 0 ? "+" : ""}${f.score}</li>`
  ).join("");
}

function renderIndicators(ind) {
  if (!ind) return;
  const order = ["rsi", "macd", "macd_signal", "macd_hist", "ema_50", "ema_200", "bb_upper", "bb_lower", "volume", "trend"];
  $("indicators").innerHTML = order.filter(k => k in ind).map(k =>
    `<div class="metric"><span class="k">${k}</span><span class="v">${typeof ind[k] === "number" ? fmt(ind[k], 4) : ind[k]}</span></div>`
  ).join("");
}

function renderMetrics(m) {
  if (!m) return;
  const rows = [
    ["Trades", m.total_trades, 0], ["Accuracy", (m.accuracy ?? 0) + "%", null],
    ["Total PnL", m.total_pnl, "pnl"], ["ROI", (m.roi_pct ?? 0) + "%", "pnl"],
    ["Win / Loss", `${m.wins}/${m.losses}`, null], ["Profit factor", m.profit_factor, 2],
    ["Sharpe", m.sharpe, 2], ["Max DD", m.max_drawdown, 2],
  ];
  $("metrics").innerHTML = rows.map(([k, v, d]) => {
    let cls = "v", txt = v;
    if (d === "pnl") { const n = Number(v); cls += n > 0 ? " up" : n < 0 ? " down" : ""; txt = fmt(v, 2); }
    else if (typeof d === "number") txt = fmt(v, d);
    return `<div class="metric"><span class="k">${k}</span><span class="${cls}">${txt}</span></div>`;
  }).join("");
  const gate = $("real-gate");
  if (m.unlocked) gate.textContent = "✅ Real trading gate unlocked (paper accuracy proven).";
  else gate.textContent = `🔒 Real locked — need ≥${m.unlock_threshold}% over ${m.min_trades}+ trades.`;
}

function renderPositions(list) {
  list = list || [];
  $("pos-count").textContent = list.length;
  $("positions").querySelector("tbody").innerHTML = list.map(p =>
    `<tr><td>${p.symbol}</td><td>${fmt(p.quantity, 6)}</td><td>${fmt(p.entry_price, 4)}</td>
     <td>${fmt(p.stop_loss, 4)}</td><td>${fmt(p.take_profit, 4)}</td></tr>`
  ).join("") || `<tr><td colspan="5" class="muted">no open positions</td></tr>`;
}

function renderActivity(list) {
  if (!list || !list.length) return;
  $("activity").innerHTML = list.slice().reverse().map(a => {
    const t = (a.ts || "").slice(11, 19);
    return `<div class="row"><span class="t">${t}</span><span class="lv-${a.level || "info"}">${escapeHtml(a.message || "")}</span></div>`;
  }).join("");
}
function escapeHtml(s) { return String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

/* ---------------- canvas charts ---------------- */
function fitCanvas(cv) {
  const dpr = window.devicePixelRatio || 1;
  const r = cv.getBoundingClientRect();
  cv.width = r.width * dpr; cv.height = r.height * dpr;
  const ctx = cv.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w: r.width, h: r.height };
}

function drawCandles() {
  const cv = $("price-chart"); if (!cv) return;
  const { ctx, w, h } = fitCanvas(cv);
  ctx.clearRect(0, 0, w, h);
  const data = state.candles.slice(-120);
  if (data.length < 2) return;
  const pad = { l: 8, r: 56, t: 8, b: 8 };
  const lows = data.map(d => d[3]), highs = data.map(d => d[2]);
  let min = Math.min(...lows), max = Math.max(...highs);
  const span = (max - min) || 1; min -= span * 0.05; max += span * 0.05;
  const x0 = pad.l, x1 = w - pad.r, y0 = pad.t, y1 = h - pad.b;
  const cw = (x1 - x0) / data.length;
  const Y = v => y1 - ((v - min) / (max - min)) * (y1 - y0);

  // grid + right-axis labels
  ctx.strokeStyle = "#1c2532"; ctx.fillStyle = "#8b98ad"; ctx.font = "11px ui-monospace,monospace"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const yy = y0 + (i / 4) * (y1 - y0), val = max - (i / 4) * (max - min);
    ctx.beginPath(); ctx.moveTo(x0, yy); ctx.lineTo(x1, yy); ctx.stroke();
    ctx.fillText(fmt(val, priceDecimals(val)), x1 + 4, yy + 3);
  }
  // candles
  data.forEach((d, i) => {
    const [, o, hi, lo, c] = d;
    const cx = x0 + i * cw + cw / 2;
    const up = c >= o; ctx.strokeStyle = ctx.fillStyle = up ? "#26a37b" : "#e5484d";
    ctx.beginPath(); ctx.moveTo(cx, Y(hi)); ctx.lineTo(cx, Y(lo)); ctx.stroke();
    const bw = Math.max(1, cw * 0.6);
    const yo = Y(o), yc = Y(c);
    ctx.fillRect(cx - bw / 2, Math.min(yo, yc), bw, Math.max(1, Math.abs(yc - yo)));
  });
  // live price line
  if (state.lastPrice != null && state.lastPrice > min && state.lastPrice < max) {
    const yy = Y(state.lastPrice);
    ctx.strokeStyle = "#3b82f6"; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(x0, yy); ctx.lineTo(x1, yy); ctx.stroke(); ctx.setLineDash([]);
  }
}

function drawEquity() {
  const cv = $("equity-chart"); if (!cv) return;
  const { ctx, w, h } = fitCanvas(cv);
  ctx.clearRect(0, 0, w, h);
  const data = state.equity.slice(-200).map(e => Number(e.equity));
  if (data.length < 2) return;
  const pad = { l: 8, r: 56, t: 10, b: 10 };
  let min = Math.min(...data), max = Math.max(...data);
  const span = (max - min) || 1; min -= span * 0.08; max += span * 0.08;
  const x0 = pad.l, x1 = w - pad.r, y0 = pad.t, y1 = h - pad.b;
  const X = i => x0 + (i / (data.length - 1)) * (x1 - x0);
  const Y = v => y1 - ((v - min) / (max - min)) * (y1 - y0);
  const rising = data[data.length - 1] >= data[0];
  ctx.strokeStyle = rising ? "#26a37b" : "#e5484d"; ctx.lineWidth = 1.6;
  ctx.beginPath(); data.forEach((v, i) => i ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v))); ctx.stroke();
  ctx.fillStyle = "#8b98ad"; ctx.font = "11px ui-monospace,monospace";
  ctx.fillText(fmt(max, 2), x1 + 4, y0 + 8); ctx.fillText(fmt(min, 2), x1 + 4, y1);
}

/* ---------------- data loads ---------------- */
async function loadSymbols() {
  try {
    const { symbols } = await apiGet("/api/symbols?quote=USDT");
    const sel = $("symbol");
    sel.innerHTML = symbols.map(s => `<option>${s}</option>`).join("");
    if (state.symbol && symbols.includes(state.symbol)) sel.value = state.symbol;
  } catch (e) { console.warn(e); }
}
async function loadCandles() {
  const { candles } = await apiGet(`/api/candles?symbol=${encodeURIComponent(state.symbol)}&timeframe=${state.timeframe}&limit=200`);
  state.candles = candles || []; drawCandles();
}
async function loadEquity() {
  const { curve } = await apiGet(`/api/equity?mode=${state.mode}`);
  state.equity = curve || []; drawEquity();
}
async function loadPanels() {
  const st0 = await apiGet("/api/status");
  state.mode = st0.active_mode || state.mode;
  const [st, m, pos, bal, act] = await Promise.all([
    Promise.resolve(st0), apiGet(`/api/metrics?mode=${state.mode}`),
    apiGet(`/api/positions?mode=${state.mode}`), apiGet("/api/balance"),
    apiGet("/api/activity?limit=60"),
  ]);
  state.symbol = st.symbol; state.timeframe = st.timeframe;
  $("symbol").value = st.symbol; $("timeframe").value = st.timeframe;
  $("chart-title").textContent = `${st.symbol} · ${st.timeframe}`;
  renderStatus(st); renderMetrics(m); renderPositions(pos.positions);
  $("balance").textContent = fmt(bal.paper_balance, 2) + " USDT";
  renderActivity(act.activity);
}

/* ---------------- websocket ---------------- */
let ws, wsRetry = 0;
function connectWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => { setConn(true); wsRetry = 0; };
  ws.onclose = () => { setConn(false); wsRetry = Math.min(wsRetry + 1, 6); setTimeout(connectWS, 500 * wsRetry); };
  ws.onerror = () => ws.close();
  ws.onmessage = (ev) => {
    let msg; try { msg = JSON.parse(ev.data); } catch { return; }
    if (msg.type === "status") { renderStatus(msg); return; }
    if (msg.type === "error") { return; }
    if (msg.type === "tick") {
      if (msg.symbol !== state.symbol || msg.timeframe !== state.timeframe) return; // stale
      if (msg.price != null) setPrice(msg.price);
      renderTicker(msg.ticker);
      renderSignal(msg.signal);
      renderIndicators(msg.indicators);
      $("running-chip").textContent = msg.running ? "running" : "idle";
      $("running-chip").classList.toggle("on", !!msg.running);
      const banner = $("halt-banner");
      if (msg.trading_allowed === false) { banner.hidden = false; banner.textContent = "⛔ " + (msg.halt_reason || "halted"); }
      else banner.hidden = true;
      // a trade opened/closed → refresh the slower panels
      if (msg.opened || (msg.closed && msg.closed.length)) { loadEquity(); loadPanels().catch(()=>{}); }
      if (msg.activity) renderActivity(msg.activity);
      drawCandles();
    }
  };
}

/* ---------------- controls ---------------- */
async function selectSymbol() {
  state.symbol = $("symbol").value; state.timeframe = $("timeframe").value;
  $("chart-title").textContent = `${state.symbol} · ${state.timeframe}`;
  await apiPost(`/api/select?symbol=${encodeURIComponent(state.symbol)}&timeframe=${state.timeframe}`);
  await Promise.all([loadCandles(), loadEquity()]);
}

function wireControls() {
  $("symbol").addEventListener("change", selectSymbol);
  $("timeframe").addEventListener("change", selectSymbol);
  $("btn-start").addEventListener("click", () => apiPost("/api/start").then(loadPanels));
  $("btn-stop").addEventListener("click", () => apiPost("/api/stop").then(loadPanels));
  $("btn-estop").addEventListener("click", () => {
    if (confirm("Emergency stop? Bot halts and won't trade until you Resume.")) apiPost("/api/emergency-stop").then(loadPanels);
  });
  $("btn-resume").addEventListener("click", () => apiPost("/api/resume").then(loadPanels));
  $("btn-reset").addEventListener("click", () => {
    if (confirm("Reset paper wallet to starting balance?")) apiPost("/api/reset-paper").then(() => { loadEquity(); loadPanels(); });
  });
  window.addEventListener("resize", () => { drawCandles(); drawEquity(); });
}

/* ---------------- boot ---------------- */
async function init() {
  wireControls();
  try {
    await loadPanels();
    await Promise.all([loadSymbols(), loadCandles(), loadEquity()]);
  } catch (e) { console.error("init failed", e); }
  connectWS();
  // gentle poll for metrics/positions in case no trades tick for a while
  setInterval(() => { apiGet(`/api/metrics?mode=${state.mode}`).then(renderMetrics).catch(()=>{}); }, 15000);
}
init();
