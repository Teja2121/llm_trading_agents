import math

STOP_VOL_MULTIPLE = 3.0      # stop distance = 3 x daily volatility
REWARD_RISK = 2.0            # take-profit distance = 2 x stop distance
RISK_PER_TRADE_PCT = 1.0     # of equity
MAX_POSITION_PCT = 10.0      # of equity

SIZE_ORDER = ["none", "quarter", "half", "full"]
SIZE_FRACTION = {"none": 0.0, "quarter": 0.25, "half": 0.5, "full": 1.0}


def compute_risk_limits(indicators: dict, equity: float) -> dict:
    price = indicators["close"]
    stop_pct = STOP_VOL_MULTIPLE * indicators["volatility_20d_daily_pct"]

    risk_budget = equity * RISK_PER_TRADE_PCT / 100
    loss_per_share = price * stop_pct / 100
    shares_by_risk = math.floor(risk_budget / loss_per_share) if loss_per_share > 0 else 0
    shares_by_cap = math.floor(equity * MAX_POSITION_PCT / 100 / price)

    return {
        "equity": equity,
        "entry_price": price,
        "stop_pct": round(stop_pct, 2),
        "stop_loss_price": round(price * (1 - stop_pct / 100), 2),
        "take_profit_price": round(price * (1 + REWARD_RISK * stop_pct / 100), 2),
        "max_shares": max(0, min(shares_by_risk, shares_by_cap)),
        "binding_constraint": "risk budget" if shares_by_risk < shares_by_cap else "position cap",
    }


def risk_flags(indicators: dict, facts: dict, market: dict) -> list[str]:
    """Plain-English warning signs, computed in code so none can be missed."""
    flags = []
    vol = indicators["volume_vs_20d_avg"]
    if vol < 0.8:
        flags.append(f"weak volume ({vol}x its 20-day average)")
    if indicators["volatility_20d_daily_pct"] > 2.5:
        flags.append(f"high volatility ({indicators['volatility_20d_daily_pct']}% daily)")
    if indicators["rsi14"] > 70:
        flags.append(f"overbought (RSI {indicators['rsi14']})")
    if indicators["rsi14"] < 30:
        flags.append(f"oversold (RSI {indicators['rsi14']})")
    ratio = facts.get("pe_to_revenue_growth_ratio")
    if ratio is not None and ratio > 2.5:
        flags.append(f"stretched valuation (P/E-to-growth {ratio})")
    above = facts.get("price_above_analyst_target_pct")
    if above is not None and above > 0:
        flags.append(f"price {above}% above analyst target")
    below_high = facts.get("pct_below_52w_high")
    if below_high is not None and below_high < 3:
        flags.append(f"within {below_high}% of 52-week high")
    if market["return_5d_pct"] < -3:
        flags.append(f"market selloff (SPY {market['return_5d_pct']}% over 5 days)")
    if market["drawdown_from_20d_high_pct"] < -5:
        flags.append(
            f"market drawdown (SPY {market['drawdown_from_20d_high_pct']}% below its 20-day high)"
        )
    return flags