# T01 Smart Binance Intelligence v2

> **Complete Rebuild with All Roadmap Features**
> 
> *Built from scratch with enhanced architecture, scalping capabilities, and professional-grade trading features*

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip
- Git

### Installation
```bash
# Clone repository
git clone <repository-url>
cd T01_Smart_Binance_v2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your settings (optional for paper trading)
nano .env  # or use any editor
```

### Run the Bot
```bash
# Start the trading bot
python -m backend.bot

# Or with custom settings
python -m backend.bot --symbol BTC/USDT --timeframe 5m --mode paper
```

### Access Dashboard
Open your browser and go to:
- **Main Dashboard:** http://127.0.0.1:8000
- **Terminal View:** http://127.0.0.1:8000/terminal

---

## 📊 Features

### ✅ Core Features (v1 - Already Working)
- Paper trading with realistic fee modeling
- 9 Technical Indicators (RSI, MACD, EMA, SMA, BB, Volume, ATR, ADX, VWAP)
- Weighted Net-Momentum Signal Engine
- Adaptive ATR-based stops/targets
- Trailing stops
- Self-learning tuner
- Loss reflection engine
- Circuit breaker
- Accuracy gate (70%+ over 50+ trades)
- Live web dashboard
- Geo-block resilience (Binance → Kraken fallback)

### 🟢 New Features (v2 - Being Built)

#### 🔴 Phase 1: Foundation (CRITICAL)
- **#10 Backtester + Walk-Forward Validation** - Validate strategy out-of-sample
- **#11 Order Reconciliation & Restart Resilience** - Never lose state

#### 🟠 Phase 2: Scalping Capabilities (HIGH)
- **#4 Real-time WebSocket Market Stream** - Sub-second data
- **#5 Multi-Timeframe Confluence** - Higher TF context
- **#8 Multi-Symbol Scanner** - Find best opportunities

#### 🟡 Phase 3: Advanced Features (HIGH)
- **#9 Exchange-Native OCO/Stop-Limit Orders** - Reliable stops
- **#7 Chart-Pattern & Market-Structure Detection** - Precise entries
- **#13 Multi-Strategy Engine + Selector** - Multiple strategies

#### 🟢 Phase 4: Futures & Expansion (MEDIUM)
- **#14 Futures + Shorting Module** - Leverage trading
- **#15 Notifications & Monitoring** - Alerts
- **#17 Advanced Pattern Detection** - More patterns

---

## 🏗️ Project Structure

```
T01_Smart_Binance_v2/
├── backend/                          # Core trading engine
│   ├── __init__.py
│   ├── config.py                    # Central configuration
│   ├── main.py                      # FastAPI server
│   ├── bot.py                       # Main trading bot
│   │
│   ├── backtesting/                 # Phase 1: Backtester
│   │   ├── __init__.py
│   │   ├── engine.py                # Backtesting engine
│   │   ├── data_loader.py           # Historical data loading
│   │   ├── walkforward.py           # Walk-forward optimization
│   │   ├── metrics.py               # Performance metrics
│   │   └── config.py                # Backtest settings
│   │
│   ├── data/                       # Data collection
│   │   ├── __init__.py
│   │   ├── collector.py             # REST API data
│   │   ├── websocket_client.py      # WebSocket connection (Phase 2)
│   │   ├── stream_manager.py        # Stream subscriptions (Phase 2)
│   │   └── data_buffer.py           # Data caching (Phase 2)
│   │
│   ├── analysis/                   # Market analysis
│   │   ├── __init__.py
│   │   ├── indicators.py            # Technical indicators
│   │   ├── signals.py               # Signal generation
│   │   ├── risk.py                  # Risk calculations
│   │   ├── multitimeframe.py        # Multi-TF analysis (Phase 2)
│   │   ├── confluence.py            # Confluence engine (Phase 2)
│   │   └── patterns/                # Pattern detection (Phase 3)
│   │       ├── __init__.py
│   │       ├── candlestick.py       # Candlestick patterns
│   │       ├── structure.py         # Market structure
│   │       ├── validator.py         # Pattern validation
│   │       └── scorer.py            # Pattern scoring
│   │
│   ├── trading/                    # Trading execution
│   │   ├── __init__.py
│   │   ├── paper_engine.py          # Paper trading
│   │   ├── real_engine.py           # Real trading
│   │   ├── order_builder.py        # Order construction (Phase 3)
│   │   ├── order_executor.py        # Exchange execution (Phase 3)
│   │   ├── order_manager.py         # Order lifecycle (Phase 1)
│   │   ├── position_manager.py      # Position tracking (Phase 1)
│   │   ├── reconciliation.py        # State reconciliation (Phase 1)
│   │   └── state_persistence.py     # State save/load (Phase 1)
│   │
│   ├── scanner/                    # Multi-symbol scanning (Phase 2)
│   │   ├── __init__.py
│   │   ├── symbol_manager.py
│   │   ├── scan_engine.py
│   │   └── results_manager.py
│   │
│   ├── strategies/                 # Multiple strategies (Phase 3)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── scalping.py
│   │   ├── swing.py
│   │   ├── trend_following.py
│   │   ├── mean_reversion.py
│   │   ├── breakout.py
│   │   └── selector.py
│   │
│   ├── futures/                    # Futures trading (Phase 4)
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exchange.py
│   │   ├── position_manager.py
│   │   ├── risk_manager.py
│   │   ├── paper_engine.py
│   │   └── real_engine.py
│   │
│   ├── safety/                     # Safety systems
│   │   └── circuit_breaker.py
│   │
│   └── ml/                        # Machine Learning (Optional)
│       ├── __init__.py
│       ├── model_loader.py
│       ├── signal_generator.py
│       └── config.py
│
├── frontend/                        # Web interface
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── components/
│       ├── Chart.jsx
│       ├── Signals.jsx
│       ├── Positions.jsx
│       ├── Scanner.jsx
│       ├── Strategies.jsx
│       └── Backtesting.jsx
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── backtesting/
│   │   ├── test_engine.py
│   │   ├── test_walkforward.py
│   │   └── test_integration.py
│   ├── data/
│   │   ├── test_collector.py
│   │   ├── test_websocket_client.py
│   │   └── test_integration.py
│   ├── trading/
│   │   ├── test_order_manager.py
│   │   ├── test_reconciliation.py
│   │   └── test_integration.py
│   ├── analysis/
│   │   ├── test_indicators.py
│   │   ├── test_signals.py
│   │   └── patterns/
│   │       ├── test_candlestick.py
│   │       └── test_structure.py
│   ├── scanner/
│   │   └── test_integration.py
│   ├── strategies/
│   │   └── test_integration.py
│   └── futures/
│       └── test_integration.py
│
├── scripts/                          # Utility scripts
│   ├── __init__.py
│   ├── collect_data.py
│   ├── run_backtest.py
│   ├── run_scanner.py
│   ├── train_model.py
│   └── utils.py
│
├── data/                            # Data storage
│   ├── historical/                   # Raw historical data
│   │   └── README.md
│   ├── processed/                    # Processed datasets
│   │   └── README.md
│   └── trades.db                     # SQLite database
│
├── models/                          # ML models (if used)
│   └── README.md
│
├── .github/                         # GitHub workflows
│   └── workflows/
│       ├── ci.yml
│       ├── test.yml
│       └── deploy.yml
│
├── docs/                            # Documentation
│   ├── architecture.md
│   ├── api.md
│   ├── configuration.md
│   ├── strategies.md
│   └── risk_management.md
│
├── .env.example                     # Environment template
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 📋 Configuration

### Environment Variables (.env)

```bash
# Binance API (for real trading - optional for paper)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true  # Use testnet for safety

# Paper Trading
PAPER_START_BALANCE=1000.0
PAPER_FEE_PCT=0.001  # 0.10%

# Accuracy Gate
ACCURACY_UNLOCK_THRESHOLD=70.0
ACCURACY_MIN_TRADES=50

# Risk Settings
RISK_PER_TRADE_PAPER=0.02  # 2%
RISK_PER_TRADE_REAL=0.01   # 1%
STOP_LOSS_PCT=0.02
TAKE_PROFIT_PCT=0.04
MAX_CONCURRENT_POSITIONS=3
DAILY_LOSS_LIMIT_PCT=0.03  # 3%

# ATR Settings
USE_ATR_STOPS=true
ATR_PERIOD=14
ATR_STOP_MULT=1.5
ATR_TP_MULT=3.0
TRAIL_ENABLED=true
TRAIL_PCT=0.015

# WebSocket
WEBSOCKET_ENABLED=true
WEBSOCKET_URL=wss://stream.binance.com:9443/ws
WEBSOCKET_RECONNECT_DELAY=1.0
WEBSOCKET_MAX_RECONNECT_DELAY=60.0

# Server
HOST=127.0.0.1
PORT=8000
TRUSTED_HOSTS=

# Default Settings
DEFAULT_SYMBOL=BTC/USDT
DEFAULT_TIMEFRAME=5m
```

---

## 🎯 Usage Examples

### Run Backtest
```bash
# Run backtest on historical data
python scripts/run_backtest.py --symbol BTC/USDT --timeframe 1h --start 2024-01-01 --end 2024-12-31

# Run walk-forward optimization
python scripts/run_backtest.py --symbol BTC/USDT --timeframe 1h --walkforward --in-sample 30 --out-sample 10
```

### Run Scanner
```bash
# Run multi-symbol scanner
python scripts/run_scanner.py --symbols BTC/USDT,ETH/USDT,SOL/USDT --timeframe 5m
```

### Run Bot with Different Modes
```bash
# Paper trading (default)
python -m backend.bot --mode paper

# Real trading (requires API keys and unlocked accuracy gate)
python -m backend.bot --mode real

# With WebSocket
python -m backend.bot --mode paper --websocket true

# Multi-symbol scanning
python -m backend.bot --mode paper --scanner true --scan-interval 60
```

---

## 🔧 Development

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test module
pytest tests/backtesting/

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
```

### Code Quality
```bash
# Linting
flake8 backend/

# Type checking
mypy backend/

# Formatting
black backend/
```

---

## 📊 Performance Metrics

The bot tracks the following metrics:

### Trading Metrics
- **Total Trades**: Number of trades executed
- **Winning Trades**: Number of profitable trades
- **Losing Trades**: Number of losing trades
- **Win Rate**: Percentage of winning trades
- **Profit Factor**: Gross Profit / Gross Loss
- **Expectancy**: Average $ edge per trade
- **Sharpe Ratio**: Risk-adjusted return
- **Max Drawdown**: Peak-to-trough decline
- **ROI**: Return on Investment

### Risk Metrics
- **Risk per Trade**: % of capital at risk per trade
- **Daily Loss Limit**: Maximum daily loss percentage
- **Liquidation Risk**: Risk of position liquidation (futures)
- **Position Exposure**: Total capital at risk

---

## 🛡️ Safety Features

### Capital Protection
1. **Paper-by-Default**: Always starts in paper trading mode
2. **Accuracy Gate**: Real trading locked until 70%+ accuracy over 50+ trades
3. **Circuit Breaker**: Emergency stop + daily loss limit
4. **Position Sizing**: Risk-based sizing (1-2% per trade)

### Operational Safety
1. **Order Reconciliation**: Syncs with exchange to prevent missed exits
2. **State Persistence**: Saves full state to survive restarts
3. **Soft Stops**: ATR-adaptive stops that scale with volatility
4. **Trailing Stops**: Lock in profits as price moves favorably

### Technical Safety
1. **DNS-Rebinding Protection**: Prevents DNS spoofing attacks
2. **CSRF Protection**: Prevents cross-site request forgery
3. **Rate Limiting**: Prevents API rate limit violations
4. **Error Handling**: Graceful degradation on failures

---

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Documentation](docs/api.md)
- [Configuration Guide](docs/configuration.md)
- [Strategy Guide](docs/strategies.md)
- [Risk Management](docs/risk_management.md)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**NOT FINANCIAL ADVICE**

Crypto trading carries real risk of loss. This bot is for educational and research purposes only. Always:

- Use paper trading first
- Start with small amounts
- Never risk more than you can afford to lose
- Understand the risks before using real money
- Use a dedicated sub-account with withdrawals disabled
- Test on Binance testnet before going live

The developers are not responsible for any losses incurred while using this software.
