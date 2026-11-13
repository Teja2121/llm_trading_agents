from statistics import mean


def _pct(x):
    """Yahoo gives fractions like 0.276; we want 27.6."""
    return None if x is None else round(x * 100, 2)


def _yoy(new, old):
    """Year-over-year change in percent."""
    if new is None or not old:
        return None
    return round((new / old - 1) * 100, 2)


def _billions(x):
    return None if x is None else round(x / 1e9, 2)


def build_fundamental_facts(
    snapshot: dict, earnings: list[dict], income: list[dict], price: float
) -> dict:
    """Merge Yahoo + Alpha Vantage data into one clean, unit-labelled dict."""
    latest = income[0] if income else {}
    year_ago = income[4] if len(income) > 4 else {}

    recent = [
        e for e in earnings[:4]
        if e["reported_eps"] is not None and e["estimated_eps"] is not None
    ]
    beats = sum(1 for e in recent if e["reported_eps"] > e["estimated_eps"])
    surprises = [e["surprise_pct"] for e in earnings[:4] if e["surprise_pct"] is not None]

    target = snapshot.get("analyst_target")
    high52 = snapshot.get("week52_high")

    revenue_yoy = _yoy(latest.get("revenue"), year_ago.get("revenue"))
    pe = snapshot.get("trailing_pe")

    return {
        "company": snapshot.get("name"),
        "sector": snapshot.get("sector"),
        "industry": snapshot.get("industry"),
        "current_price": price,
        "market_cap_billions_usd": _billions(snapshot.get("market_cap")),
        "trailing_pe": snapshot.get("trailing_pe"),
        "forward_pe": snapshot.get("forward_pe"),
        "eps_trailing_12m": snapshot.get("eps"),
        "beta": snapshot.get("beta"),
        # Yahoo already reports dividend yield in percent (0.3 means 0.3%)
        "dividend_yield_pct": snapshot.get("dividend_yield"),
        "profit_margin_pct": _pct(snapshot.get("profit_margin")),
        "revenue_growth_yoy_pct_per_yahoo": _pct(snapshot.get("revenue_growth")),
        "pct_below_52w_high": _yoy(price, high52) and round(-_yoy(price, high52), 2),
        "pct_vs_analyst_target": _yoy(price, target),
        "latest_quarter_end": latest.get("fiscal_date"),
        "latest_quarter_revenue_billions_usd": _billions(latest.get("revenue")),
        "revenue_yoy_pct": revenue_yoy,
        "pe_to_revenue_growth_ratio": (
            round(pe / revenue_yoy, 2) if pe and revenue_yoy and revenue_yoy > 0 else None
        ),
        "price_above_analyst_target_pct": _yoy(price, target),
        "net_income_yoy_pct": _yoy(latest.get("net_income"), year_ago.get("net_income")),
        "net_margin_latest_quarter_pct": (
            round(latest["net_income"] / latest["revenue"] * 100, 2)
            if latest.get("net_income") and latest.get("revenue")
            else None
        ),
        "eps_beats_last_4_quarters": f"{beats} of {len(recent)}",
        "avg_eps_surprise_last_4_quarters_pct": (
            round(mean(surprises), 2) if surprises else None
        ),
    }