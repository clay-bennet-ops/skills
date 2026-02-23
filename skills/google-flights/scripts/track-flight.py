#!/usr/bin/env python3
"""Track a flight route for price monitoring."""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from itertools import product

from fli.models import (
    Airport,
    FlightSearchFilters,
    FlightSegment,
    MaxStops,
    PassengerInfo,
    SeatType,
    TripType,
)
from search_utils import search_with_currency, filter_results, DEFAULT_EXCLUDE

SEAT_MAP = {
    "economy": SeatType.ECONOMY,
    "premium": SeatType.PREMIUM_ECONOMY,
    "business": SeatType.BUSINESS,
    "first": SeatType.FIRST,
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TRACKED_FILE = os.path.join(DATA_DIR, "tracked.json")


def load_tracked():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE) as f:
            return json.load(f)
    return []


def save_tracked(tracked):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TRACKED_FILE, "w") as f:
        json.dump(tracked, f, indent=2)


def parse_args():
    p = argparse.ArgumentParser(description="Track a flight for price alerts")
    p.add_argument("origin", help="Origin airport(s)")
    p.add_argument("destination", help="Destination airport(s)")
    p.add_argument("date", help="Departure date (YYYY-MM-DD)")
    p.add_argument("--return-date", "-r", help="Return date")
    p.add_argument("--adults", "-a", type=int, default=1)
    p.add_argument("--cabin", "-c", default="economy", choices=SEAT_MAP.keys())
    p.add_argument("--stops", default="nonstop", choices=["any", "nonstop", "1", "2"])
    p.add_argument("--target-price", "-t", type=float, help="Alert when price drops below this (per person)")
    p.add_argument("--exclude", help="Exclude airlines (default: NK,F9)")
    p.add_argument("--no-exclude", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    tracked = load_tracked()

    origins = [o.strip().upper() for o in args.origin.split(",")]
    destinations = [d.strip().upper() for d in args.destination.split(",")]

    exclude = set() if args.no_exclude else (
        {c.strip().upper() for c in args.exclude.split(",")} if args.exclude else DEFAULT_EXCLUDE
    )

    stops_map = {"any": MaxStops.ANY, "nonstop": MaxStops.NON_STOP, "1": MaxStops.ONE_STOP_OR_FEWER, "2": MaxStops.TWO_OR_FEWER_STOPS}
    added = 0

    for orig, dest in product(origins, destinations):
        route_id = f"{orig}-{dest}-{args.date}"
        if args.return_date:
            route_id += f"-RT-{args.return_date}"
        route_id += f"-{args.adults}pax"

        if any(t["id"] == route_id for t in tracked):
            print(f"Already tracking {route_id}")
            continue

        try:
            origin = Airport[orig]
            destination = Airport[dest]
        except KeyError as e:
            print(f"Unknown airport: {e}", file=sys.stderr)
            continue

        segments = [FlightSegment(departure_airport=[[origin, 0]], arrival_airport=[[destination, 0]], travel_date=args.date)]
        trip_type = TripType.ONE_WAY
        if args.return_date:
            segments.append(FlightSegment(departure_airport=[[destination, 0]], arrival_airport=[[origin, 0]], travel_date=args.return_date))
            trip_type = TripType.ROUND_TRIP

        filters = FlightSearchFilters(
            trip_type=trip_type,
            passenger_info=PassengerInfo(adults=args.adults),
            flight_segments=segments,
            seat_type=SEAT_MAP[args.cabin],
            stops=stops_map[args.stops],
        )

        print(f"Searching {orig} → {dest} on {args.date}...")
        results, currency = search_with_currency(filters, top_n=5)

        now = datetime.now(timezone.utc).isoformat()
        price_entry = {"timestamp": now, "best_price": None, "airline": None}

        if results:
            results = filter_results(results, exclude_airlines=exclude, is_round_trip=bool(args.return_date))
            if results:
                flight = results[0]
                if isinstance(flight, tuple):
                    price_entry["best_price"] = round(flight[0].price + flight[1].price, 2)
                    price_entry["airline"] = flight[0].legs[0].airline.name if flight[0].legs else None
                else:
                    price_entry["best_price"] = round(flight.price, 2)
                    price_entry["airline"] = flight.legs[0].airline.name if flight.legs else None

        entry = {
            "id": route_id,
            "origin": orig,
            "destination": dest,
            "date": args.date,
            "return_date": args.return_date,
            "adults": args.adults,
            "cabin": args.cabin,
            "stops": args.stops,
            "target_price": args.target_price,
            "exclude_airlines": list(exclude),
            "currency": currency,
            "added_at": now,
            "price_history": [price_entry],
        }

        tracked.append(entry)
        added += 1

        if price_entry["best_price"]:
            print(f"  ${price_entry['best_price']:.0f} ({price_entry['airline']})")
        else:
            print(f"  No qualifying flights found")

    save_tracked(tracked)
    print(f"\nTracking {added} new route(s). Total tracked: {len(tracked)}")
    if args.target_price:
        print(f"Target: ${args.target_price:.0f}/pp")


if __name__ == "__main__":
    main()
