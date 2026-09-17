import pandas as pd
from agents.T01_Smart_Binance_Intelligence.backend.analysis import indicators
from agents.T01_Smart_Binance_Intelligence.backend.analysis import risk

def test_atr():
    df = pd.DataFrame({
        "high": [10, 12, 11, 15],
        "low": [8, 9, 7, 10],
        "close": [9, 11, 10, 14]
    })
    tr = indicators.atr(df, period=2)
    assert not tr.iloc[-1] == 0

def test_dynamic_risk():
    balance = 1000
    price = 100
    qty = risk.position_size(balance, price, mode="paper", atr=5.0)
    assert qty > 0
