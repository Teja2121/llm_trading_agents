import argparse


def cmd_run(args) -> None:
    from trading_agents.graph import build_graph  # imported lazily: keeps --help fast

    app = build_graph()
    rows = []
    for ticker in (t.upper() for t in args.tickers):
        print(f"\n=== {ticker} ===")
        try:
            final = app.invoke(
                {
                    "ticker": ticker, "debate": [], "adjustments": [], "round": 0,
                    "max_rounds": args.rounds, "equity": args.equity, "position_shares": 0,
                }
            )
        except Exception as e:  # one bad ticker must not stop the others
            print(f"{ticker} failed: {e}")
            rows.append((ticker, "ERROR", 0, "-", "-"))
            continue

        decision = final["decision"]
        rows.append((ticker, decision.action, decision.shares, decision.confidence,
                     final["outcome"].leaning))
        if args.verbose:
            print(decision.model_dump_json(indent=2))
            print("code adjustments:", final["adjustments"] or "none")

    print("\n=== SUMMARY ===")
    print(f"{'TICKER':<8}{'ACTION':<8}{'SHARES':<8}{'CONF':<7}VERDICT")
    for ticker, action, shares, conf, verdict in rows:
        print(f"{ticker:<8}{action:<8}{shares:<8}{conf!s:<7}{verdict}")


def cmd_evaluate(args) -> None:
    from trading_agents.evaluate import evaluate_pending

    print(f"{evaluate_pending()} decision(s) evaluated.")


def cmd_reflect(args) -> None:
    from trading_agents.reflect import reflect_pending

    print(f"{reflect_pending()} decision(s) reflected on.")


def cmd_history(args) -> None:
    from trading_agents.decision_log import format_row, recent_decisions

    rows = recent_decisions(limit=args.limit)
    if not rows:
        print("No decisions logged yet.")
    for r in rows:
        print(format_row(r))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="trading_agents",
        description="Multi-agent LLM paper-trading research (decision support, not financial advice)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="analyse one or more tickers")
    run.add_argument("tickers", nargs="+")
    run.add_argument("--rounds", type=int, default=2, help="debate rounds")
    run.add_argument("--equity", type=float, default=100_000.0, help="paper equity")
    run.add_argument("--verbose", action="store_true")
    run.set_defaults(func=cmd_run)

    sub.add_parser("evaluate", help="score past decisions").set_defaults(func=cmd_evaluate)
    sub.add_parser("reflect", help="turn outcomes into lessons").set_defaults(func=cmd_reflect)

    hist = sub.add_parser("history", help="show recent decisions")
    hist.add_argument("--limit", type=int, default=10)
    hist.set_defaults(func=cmd_history)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()