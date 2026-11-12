import pandas as pd


def _r(x) -> float:
    return round(float(x), 2)


def compute_indicators(prices: list[dict]) -> dict:
    """Turn raw OHLCV rows into the handful of numbers a technical analyst uses."""
    df = pd.DataFrame(prices)
    close = df["close"]

    # Moving averages: average closing price over the last N days
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()

    # RSI (Wilder): ratio of average gains to average losses over ~14 days
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + avg_gain / avg_loss)

    # MACD: fast EMA minus slow EMA, and a smoothed "signal" line of that
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    last = close.iloc[-1]
    return {
        "as_of": df["date"].iloc[-1],
        "close": _r(last),
        "sma20": _r(sma20.iloc[-1]),
        "sma50": _r(sma50.iloc[-1]),
        "price_vs_sma50_pct": _r((last / sma50.iloc[-1] - 1) * 100),
        "rsi14": _r(rsi.iloc[-1]),
        "macd": _r(macd.iloc[-1]),
        "macd_signal": _r(signal.iloc[-1]),
        "macd_histogram": _r(macd.iloc[-1] - signal.iloc[-1]),
        "return_1m_pct": _r((last / close.iloc[-22] - 1) * 100),
        "return_3m_pct": _r((last / close.iloc[-64] - 1) * 100),
        "volatility_20d_daily_pct": _r(close.pct_change().tail(20).std() * 100),
        "volume_vs_20d_avg": _r(df["volume"].iloc[-1] / df["volume"].tail(20).mean()),
    }