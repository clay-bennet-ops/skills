#!/usr/bin/env python3
"""Check all tracked flights for price changes. Designed for cron."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from fli.models import (
    Airport,
    FlightSearchFilters,
    FlightSegment,
    MaxStops,
    PassengerInfo,
    SeatType,
    TripType,
)
from search_utils import search_with_currency, filter_results

SEAT_MAP = {"economy": SeatType.ECONOMY, "premium": SeatType.PREMIUM_ECONOMY, "business": SeatType.BUSINESS, "first": SeatType.FIRST}
STOPS_MAP = {"any": MaxStops.ANY, "nonstop": MaxStops.NON_STOP, "1": MaxStops.ONE_STOP_OR_FEWER, "2": MaxStops.TWO_OR_FEWER_STOPS}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TRACKED_FILE = os.path.join(DATA_DIR, "tracked.json")


def load_tracked():
    if not os.path.exists(TRACKED_FILE):
        return []
    with open(TRACKED_FILE) as f:
        return json.load(f)


def save_tracked(tracked):
    with open(TRACKED_FILE, "w") as f:
        json.dump(tracked, f, indent=2)


def check_route(entry):
    origin = Airport[entry["origin"]]
    destination = Airport[entry["destination"]]

    segments = [FlightSegment(departure_airport=[[origin, 0]], arrival_airport=[[destination, 0]], travel_date=entry["date"])]
    trip_type = TripType.ONE_WAY
    if entry.get("return_date"):
        segments.append(FlightSegment(departure_airport=[[destination, 0]], arrival_airport=[[origin, 0]], travel_date=entry["return_date"]))
        trip_type = TripType.ROUND_TRIP

    filters = FlightSearchFilters(
        trip_type=trip_type,
        passenger_info=PassengerInfo(adults=entry.get("adults", 1)),
        flight_segments=segments,
        seat_type=SEAT_MAP.get(entry.get("cabin", "economy"), SeatType.ECONOMY),
        stops=STOPS_MAP.get(entry.get("stops", "any"), MaxStops.ANY),
    )

    results, currency = search_with_currency(filters, top_n=5)
    if not results:
        return None, None, currency

    exclude = set(entry.get("exclude_airlines", ["NK", "F9"]))
    results = filter_results(results, exclude_airlines=exclude, is_round_trip=bool(entry.get("return_date")))
    if not results:
        return None, None, currency

    flight = results[0]
    if isinstance(flight, tuple):
        price = round(flight[0].price + flight[1].price, 2)
        airline = flight[0].legs[0].airline.name if flight[0].legs else None
    else:
        price = round(flight.price, 2)
        airline = flight.legs[0].airline.name if flight.legs else None

    return price, airline, currency


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=float, default=10, help="Percent drop to alert (default: 10)")
    p.add_argument("--json", action="store_true", help="Output alerts as JSON")
    args = p.parse_args()

    tracked = load_tracked()
    if not tracked:
        print("No flights tracked.")
        sys.exit(0)

    now = datetime.now(timezone.utc).isoformat()
    alerts = []
    summary = []

    for entry in tracked:
        route = f"{entry['origin']}→{entry['destination']} {entry['date']}"
        if entry.get("return_date"):
            route += f" RT {entry['return_date']}"
        route += f" ({entry.get('adults', 1)}pax)"

        try:
            price, airline, currency = check_route(entry)
        except Exception as e:
            print(f"Error checking {route}: {e}", file=sys.stderr)
            continue

        if price is None:
            summary.append({"route": route, "status": "no_results"})
            continue

        entry["price_history"].append({"timestamp": now, "best_price": price, "airline": airline})
        entry["currency"] = currency

        prev_prices = [p["best_price"] for p in entry["price_history"][:-1] if p["best_price"]]
        status = "first_check"
        change = 0
        pct = 0

        if prev_prices:
            last_price = prev_prices[-1]
            change = price - last_price
            pct = (change / last_price) * 100 if last_price else 0

            if change < 0:
                status = "down"
                if abs(pct) >= args.threshold:
                    alerts.append({
                        "type": "price_drop",
                        "route": route,
                        "price": price,
                        "was": last_price,
                        "drop_pct": round(abs(pct), 1),
                        "airline": airline,
                    })
            elif change > 0:
                status = "up"
            else:
                status = "unchanged"

        # Target price alert
        if entry.get("target_price") and price <= entry["target_price"]:
            alerts.append({
                "type": "target_reached",
                "route": route,
                "price": price,
                "target": entry["target_price"],
                "airline": airline,
            })

        summary.append({
            "route": route,
            "price": price,
            "airline": airline,
            "status": status,
            "change": round(change, 2),
            "change_pct": round(pct, 1),
        })

    save_tracked(tracked)

    if args.json:
        print(json.dumps({"alerts": alerts, "summary": summary}, indent=2))
    else:
        for s in summary:
            if s.get("status") == "no_results":
                print(f"  {s['route']}: no results")
            elif s["status"] == "first_check":
                print(f"  {s['route']}: ${s['price']:.0f} ({s['airline']})")
            elif s["status"] == "down":
                print(f"  {s['route']}: ${s['price']:.0f} ↓${abs(s['change']):.0f} ({abs(s['change_pct']):.1f}%)")
            elif s["status"] == "up":
                print(f"  {s['route']}: ${s['price']:.0f} ↑${s['change']:.0f} ({s['change_pct']:.1f}%)")
            else:
                print(f"  {s['route']}: ${s['price']:.0f} (unchanged)")

        if alerts:
            print(f"\n{'='*50}")
            print("🚨 ALERTS:")
            for a in alerts:
                if a["type"] == "price_drop":
                    print(f"  PRICE DROP: {a['route']} now ${a['price']:.0f} (was ${a['was']:.0f}, down {a['drop_pct']}%)")
                elif a["type"] == "target_reached":
                    print(f"  TARGET HIT: {a['route']} now ${a['price']:.0f} (target: ${a['target']:.0f})")


if __name__ == "__main__":
    main()
