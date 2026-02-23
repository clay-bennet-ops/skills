#!/usr/bin/env python3
"""List all tracked flights."""

import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TRACKED_FILE = os.path.join(DATA_DIR, "tracked.json")


def main():
    if not os.path.exists(TRACKED_FILE):
        print("No flights tracked.")
        sys.exit(0)

    with open(TRACKED_FILE) as f:
        tracked = json.load(f)

    if not tracked:
        print("No flights tracked.")
        sys.exit(0)

    for entry in tracked:
        route = f"{entry['origin']}→{entry['destination']}"
        print(f"\n{'='*50}")
        print(f"{route} | {entry['date']} | {entry.get('cabin', 'economy')} | {entry.get('adults', 1)}pax")
        if entry.get("return_date"):
            print(f"  Return: {entry['return_date']}")
        if entry.get("target_price"):
            print(f"  Target: ${entry['target_price']:.0f}")
        if entry.get("exclude_airlines"):
            print(f"  Excluding: {', '.join(entry['exclude_airlines'])}")

        history = entry.get("price_history", [])
        if not history:
            print("  No price data")
            continue

        first_price = next((p["best_price"] for p in history if p["best_price"]), None)
        last = history[-1]
        current = last.get("best_price")

        if current and first_price:
            change = current - first_price
            pct = (change / first_price) * 100
            arrow = "↓" if change < 0 else "↑" if change > 0 else "→"
            print(f"  Current: ${current:.0f} ({last.get('airline', '?')})")
            print(f"  Original: ${first_price:.0f} | {arrow} ${abs(change):.0f} ({abs(pct):.1f}%)")
        elif current:
            print(f"  Current: ${current:.0f} ({last.get('airline', '?')})")

        print(f"  Checks: {len(history)} | Since: {entry.get('added_at', '?')[:10]}")

    print(f"\n{len(tracked)} flight(s) tracked.")


if __name__ == "__main__":
    main()
