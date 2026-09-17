import pytest
from backend.bot import TradingBot
from backend.data import database as db


@pytest.mark.asyncio
async def test_bot_cycle_paper_trade():
    db.init_db()
    bot = TradingBot()
    bot.start()

    # Run one cycle; it will use ccxt.kraken fallback if binance 451
    await bot._cycle()

    # Check if bot processed the cycle and populated price
    assert bot.last_price is not None
    assert bot.last_price > 0
    assert bot.active_mode == "paper"
