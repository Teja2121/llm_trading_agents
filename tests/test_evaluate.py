from trading_agents.evaluate import label_outcome, simulate_trade


def day(date, o, h, l, c):
    return {"date": date, "open": o, "high": h, "low": l, "close": c, "volume": 1}


BASE = day("2026-01-01", 100, 100, 100, 100)  # the decision day (entry 100)


def test_stop_hit():
    prices = [BASE, day("2026-01-02", 100, 101, 94, 95), day("2026-01-03", 95, 96, 94, 95)]
    r = simulate_trade(prices, "2026-01-01", 100, 95, 110, horizon=2)
    assert r["exit_reason"] == "stop hit" and r["return_pct"] == -5.0


def test_target_hit():
    prices = [BASE, day("2026-01-02", 100, 111, 99, 108), day("2026-01-03", 108, 109, 107, 108)]
    r = simulate_trade(prices, "2026-01-01", 100, 95, 110, horizon=2)
    assert r["exit_reason"] == "target hit" and r["return_pct"] == 10.0


def test_horizon_exit():
    prices = [BASE, day("2026-01-02", 100, 102, 99, 101), day("2026-01-03", 101, 103, 100, 102)]
    r = simulate_trade(prices, "2026-01-01", 100, 95, 110, horizon=2)
    assert r["exit_reason"] == "horizon" and r["return_pct"] == 2.0


def test_gap_down_fills_at_open():
    prices = [BASE, day("2026-01-02", 90, 92, 89, 91), day("2026-01-03", 91, 92, 90, 91)]
    r = simulate_trade(prices, "2026-01-01", 100, 95, 110, horizon=2)
    assert r["exit_price"] == 90 and r["return_pct"] == -10.0


def test_not_enough_days_returns_none():
    prices = [BASE, day("2026-01-02", 100, 101, 99, 100)]
    assert simulate_trade(prices, "2026-01-01", 100, 95, 110, horizon=5) is None


def test_labels():
    assert label_outcome("BUY", 2.0) == "good"
    assert label_outcome("BUY", -2.0) == "bad"
    assert label_outcome("BUY", 0.5) == "neutral"
    assert label_outcome("HOLD", 5.0) == "bad"     # missed a rally
    assert label_outcome("HOLD", -3.0) == "good"   # avoided a drop