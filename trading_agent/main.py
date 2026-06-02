"""Entry point for the Claude-powered stock market analyst agent.

Examples:
    python main.py                 # one analysis+trade pass (paper mode)
    python main.py --loop 15       # repeat every 15 minutes
    python main.py --reset         # wipe saved state and start fresh
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time

import config


def _preflight() -> bool:
    ok = True
    if config.BRAIN == "api":
        if not config.ANTHROPIC_API_KEY:
            print("ERROR: BRAIN=api but ANTHROPIC_API_KEY is not set. Add it to "
                  ".env, or use BRAIN=claude_code to use your subscription.")
            ok = False
    else:  # claude_code
        if not shutil.which(config.CLAUDE_CLI):
            print(f"ERROR: BRAIN=claude_code but '{config.CLAUDE_CLI}' is not on "
                  "PATH. Install Claude Code and log in with your subscription "
                  "(claude login), or set BRAIN=api.")
            ok = False
    if config.TRADING_MODE == "live":
        print("WARNING: TRADING_MODE=live, but LiveBroker is a stub. Real orders "
              "will not be placed until you implement it. Use 'paper' to test.")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude stock analyst agent")
    parser.add_argument("--loop", type=int, metavar="MINUTES",
                        help="run repeatedly every N minutes")
    parser.add_argument("--reset", action="store_true",
                        help="delete saved portfolio state before running")
    args = parser.parse_args()

    if args.reset and os.path.exists(config.STATE_FILE):
        os.remove(config.STATE_FILE)
        print("State reset.")

    if not _preflight():
        return 1

    # Imported here so --reset / preflight work even without deps installed.
    from runner import TradingAgent

    agent = TradingAgent()
    print(f"Brain: {agent.analyst.label} | Mode: {config.TRADING_MODE} | "
          f"Capital: ₹{config.STARTING_CAPITAL:,.0f} | "
          f"Monthly target: {config.MONTHLY_TARGET_PCT*100:.0f}%")

    if not args.loop:
        agent.run_once()
        return 0

    print(f"Looping every {args.loop} min. Ctrl-C to stop.")
    try:
        while True:
            agent.run_once()
            time.sleep(args.loop * 60)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
