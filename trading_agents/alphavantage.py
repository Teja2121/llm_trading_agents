import json
import time

import requests

from trading_agents.config import get_settings
from trading_agents.db import cache_get, cache_set

BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageError(Exception):
    """Raised when Alpha Vantage returns an error or a rate-limit message."""

MIN_INTERVAL = 1.2  # seconds between API calls (free tier burst limit is ~1/sec)

def _num(value):
    """Alpha Vantage sends numbers as strings, sometimes 'None'. Convert safely."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

class AlphaVantageClient:
    def __init__(self):
        self.api_key = get_settings().alphavantage_api_key
        self._last_call = 0.0

    def _request(self, function: str, cache_hours: float, **params) -> dict:
        cache_key = f"{function}:{json.dumps(params, sort_keys=True)}"

        cached = cache_get(cache_key, cache_hours)
        if cached is not None:
            print(f"[cache hit] {cache_key}")
            return cached

        wait = MIN_INTERVAL - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)

        print(f"[API call]  {cache_key}")
        response = requests.get(
            BASE_URL,
            params={"function": function, "apikey": self.api_key, **params},
            timeout=30,
        )
        self._last_call = time.monotonic()
        response.raise_for_status()
        data = response.json()

        for field in ("Error Message", "Note", "Information"):
            if field in data:
                raise AlphaVantageError(data[field])

        cache_set(cache_key, data)
        return data

    def daily_prices(self, symbol: str) -> list[dict]:
        """Last ~100 trading days of OHLCV, oldest first."""
        raw = self._request(
            "TIME_SERIES_DAILY", 6, symbol=symbol, outputsize="compact"
        )
        series = raw["Time Series (Daily)"]
        rows = [
            {
                "date": day,
                "open": float(v["1. open"]),
                "high": float(v["2. high"]),
                "low": float(v["3. low"]),
                "close": float(v["4. close"]),
                "volume": int(v["5. volume"]),
            }
            for day, v in series.items()
        ]
        rows.sort(key=lambda r: r["date"])
        return rows

    def earnings(self, symbol: str, quarters: int = 8) -> list[dict]:
        """Quarterly EPS: what the company reported vs. what analysts expected."""
        raw = self._request("EARNINGS", 24 * 7, symbol=symbol)
        return [
            {
                "fiscal_date": q.get("fiscalDateEnding"),
                "reported_date": q.get("reportedDate"),
                "reported_eps": _num(q.get("reportedEPS")),
                "estimated_eps": _num(q.get("estimatedEPS")),
                "surprise_pct": _num(
                    q.get("surprisePercentage", q.get("surprisePercent"))
                ),
            }
            for q in raw.get("quarterlyEarnings", [])[:quarters]
        ]

    def income_statement(self, symbol: str, quarters: int = 4) -> list[dict]:
        """Revenue and profit for the most recent quarters."""
        raw = self._request("INCOME_STATEMENT", 24 * 7, symbol=symbol)
        return [
            {
                "fiscal_date": q.get("fiscalDateEnding"),
                "revenue": _num(q.get("totalRevenue")),
                "gross_profit": _num(q.get("grossProfit")),
                "operating_income": _num(q.get("operatingIncome")),
                "net_income": _num(q.get("netIncome")),
            }
            for q in raw.get("quarterlyReports", [])[:quarters]
        ]

if __name__ == "__main__":
    av = AlphaVantageClient()
    prices = av.daily_prices("AAPL")
    print("Days of data:", len(prices), "| latest:", prices[-1])
    print("Earnings:", av.earnings("AAPL", quarters=2))
    print("Income:", av.income_statement("AAPL", quarters=1))