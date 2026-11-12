import yfinance as yf

from trading_agents.db import cache_get, cache_set

# our field name -> Yahoo's field name
SNAPSHOT_FIELDS = {
    "name": "shortName",
    "sector": "sector",
    "industry": "industry",
    "market_cap": "marketCap",
    "trailing_pe": "trailingPE",
    "forward_pe": "forwardPE",
    "eps": "trailingEps",
    "dividend_yield": "dividendYield",
    "profit_margin": "profitMargins",
    "revenue_growth": "revenueGrowth",
    "beta": "beta",
    "week52_high": "fiftyTwoWeekHigh",
    "week52_low": "fiftyTwoWeekLow",
    "analyst_target": "targetMeanPrice",
}


class YahooClient:
    def snapshot(self, symbol: str) -> dict:
        """Valuation and company profile, cached for a day."""
        key = f"YF_INFO:{symbol}"
        cached = cache_get(key, 24)
        if cached is not None:
            print(f"[cache hit] {key}")
            return cached

        print(f"[yfinance]  {key}")
        info = yf.Ticker(symbol).info
        data = {ours: info.get(theirs) for ours, theirs in SNAPSHOT_FIELDS.items()}
        if data["name"] is None:
            raise RuntimeError(f"No Yahoo data returned for {symbol}")
        cache_set(key, data)
        return data

    def news(self, symbol: str, limit: int = 8) -> list[dict]:
        """Recent headlines (no sentiment score; our news agent will judge it)."""
        key = f"YF_NEWS:{symbol}:{limit}"
        cached = cache_get(key, 3)
        if cached is not None:
            print(f"[cache hit] {key}")
            return cached

        print(f"[yfinance]  {key}")
        items = yf.Ticker(symbol).news or []
        results = []
        for item in items[:limit]:
            # Yahoo changed its format: newer items nest fields under "content".
            c = item.get("content", item)
            provider = c.get("provider") or {}
            results.append(
                {
                    "title": c.get("title"),
                    "summary": c.get("summary"),
                    "source": provider.get("displayName") or c.get("publisher"),
                    "published": c.get("pubDate") or c.get("providerPublishTime"),
                }
            )
        cache_set(key, results)
        return results


if __name__ == "__main__":
    yc = YahooClient()
    print("Snapshot:", yc.snapshot("AAPL"))
    for h in yc.news("AAPL", limit=3):
        print("-", h["title"], "|", h["source"], "|", h["published"])