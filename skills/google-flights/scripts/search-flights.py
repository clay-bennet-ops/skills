#!/usr/bin/env python3
"""Search Google Flights for a route and date. Outputs JSON or text."""

import argparse
import json
import sys
from datetime import datetime, timedelta
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
from search_utils import (
    search_with_currency, filter_results, format_results, format_text,
    DEFAULT_EXCLUDE,
)

SEAT_MAP = {
    "economy": SeatType.ECONOMY,
    "premium": SeatType.PREMIUM_ECONOMY,
    "business": SeatType.BUSINESS,
    "first": SeatType.FIRST,
}

STOPS_MAP = {
    "any": MaxStops.ANY,
    "nonstop": MaxStops.NON_STOP,
    "1": MaxStops.ONE_STOP_OR_FEWER,
    "2": MaxStops.TWO_OR_FEWER_STOPS,
}


def parse_args():
    p = argparse.ArgumentParser(description="Search Google Flights")
    p.add_argument("origin", help="Origin airport(s), comma-separated (e.g. JFK,EWR,LGA)")
    p.add_argument("destination", help="Destination airport(s), comma-separated")
    p.add_argument("date", help="Departure date (YYYY-MM-DD)")
    p.add_argument("--date-to", help="End of date range (searches each day)")
    p.add_argument("--return-date", "-r", help="Return date for round trips")
    p.add_argument("--adults", "-a", type=int, default=1, help="Number of adults (default: 1)")
    p.add_argument("--cabin", "-c", default="economy", choices=SEAT_MAP.keys())
    p.add_argument("--stops", "-s", default="any", choices=STOPS_MAP.keys())
    p.add_argument("--results", "-n", type=int, default=10, help="Max results per search")
    p.add_argument("--exclude", help="Exclude airlines (IATA codes, comma-separated). Default: NK,F9")
    p.add_argument("--no-exclude", action="store_true", help="Don't exclude any airlines")
    p.add_argument("--include", help="Only include these airlines (IATA codes, comma-separated)")
    p.add_argument("--after", type=int, help="Depart after this hour (24h, e.g. 17 = 5pm)")
    p.add_argument("--before", type=int, help="Depart before this hour (24h)")
    p.add_argument("--max-duration", type=int, help="Max flight duration in minutes")
    p.add_argument("--output", "-o", default="json", choices=["json", "text"], help="Output format")
    p.add_argument("--separate", action="store_true",
                   help="Search each direction as separate one-ways (finds cheaper 'separate tickets' combos)")
    p.add_argument("--sort", default="price", choices=["price", "duration", "stops"])
    return p.parse_args()


def expand_dates(date_str, date_to_str=None):
    start = datetime.strptime(date_str, "%Y-%m-%d").date()
    end = datetime.strptime(date_to_str, "%Y-%m-%d").date() if date_to_str else start
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def main():
    args = parse_args()

    origins = [o.strip().upper() for o in args.origin.split(",")]
    destinations = [d.strip().upper() for d in args.destination.split(",")]
    dates = expand_dates(args.date, args.date_to)

    # Airline filters
    if args.no_exclude:
        exclude = set()
    elif args.exclude:
        exclude = {c.strip().upper() for c in args.exclude.split(",")}
    else:
        exclude = DEFAULT_EXCLUDE

    include = {c.strip().upper() for c in args.include.split(",")} if args.include else None

    is_round_trip = bool(args.return_date)
    use_separate = args.separate and is_round_trip
    all_results = []

    for orig_code, dest_code, date in product(origins, destinations, dates):
        try:
            origin = Airport[orig_code]
            destination = Airport[dest_code]
        except KeyError as e:
            print(f"Unknown airport: {e}", file=sys.stderr)
            continue

        if use_separate:
            # Search each direction as independent one-ways, then combine
            print(f"Searching {orig_code} → {dest_code} on {date} (separate outbound)...", file=sys.stderr)
            out_filters = FlightSearchFilters(
                trip_type=TripType.ONE_WAY,
                passenger_info=PassengerInfo(adults=args.adults),
                flight_segments=[FlightSegment(
                    departure_airport=[[origin, 0]],
                    arrival_airport=[[destination, 0]],
                    travel_date=date,
                )],
                seat_type=SEAT_MAP[args.cabin],
                stops=STOPS_MAP[args.stops],
            )
            out_results, currency = search_with_currency(out_filters, top_n=args.results)

            print(f"Searching {dest_code} → {orig_code} on {args.return_date} (separate return)...", file=sys.stderr)
            ret_filters = FlightSearchFilters(
                trip_type=TripType.ONE_WAY,
                passenger_info=PassengerInfo(adults=args.adults),
                flight_segments=[FlightSegment(
                    departure_airport=[[destination, 0]],
                    arrival_airport=[[origin, 0]],
                    travel_date=args.return_date,
                )],
                seat_type=SEAT_MAP[args.cabin],
                stops=STOPS_MAP[args.stops],
            )
            ret_results, ret_currency = search_with_currency(ret_filters, top_n=args.results)

            if not out_results or not ret_results:
                print(f"  No results for one or both directions.", file=sys.stderr)
                continue

            # Filter each direction independently
            out_results = filter_results(out_results, exclude_airlines=exclude,
                include_airlines=include, depart_after=args.after,
                depart_before=args.before, max_duration=args.max_duration,
                is_round_trip=False)
            ret_results = filter_results(ret_results, exclude_airlines=exclude,
                include_airlines=include, depart_after=args.after,
                depart_before=args.before, max_duration=args.max_duration,
                is_round_trip=False)

            if not out_results or not ret_results:
                print(f"  No results after filtering.", file=sys.stderr)
                continue

            # Sort each direction by price, take top N
            out_results.sort(key=lambda x: x.price)
            ret_results.sort(key=lambda x: x.price)
            out_top = out_results[:args.results]
            ret_top = ret_results[:args.results]

            # Combine: pair each outbound with each return, sort by total, take top N
            pairs = []
            for o in out_top:
                for r in ret_top:
                    pairs.append((o, r))

            if args.sort == "price":
                pairs.sort(key=lambda x: x[0].price + x[1].price)
            elif args.sort == "duration":
                pairs.sort(key=lambda x: x[0].duration + x[1].duration)

            results = pairs[:args.results]

            if args.output == "json":
                formatted = format_results(results, currency, is_round_trip=True)
                for f in formatted:
                    f["search"] = {"origin": orig_code, "destination": dest_code,
                                   "date": date, "return_date": args.return_date,
                                   "separate_tickets": True}
                all_results.extend(formatted)
            else:
                print(f"\n{'='*60}")
                print(f"{orig_code} → {dest_code} | {date} | {args.cabin} | {args.adults} pax | {currency}")
                print(f"Return: {args.return_date} | ⚠️  SEPARATE TICKETS (not bundled)")
                print(format_text(results, currency, is_round_trip=True))
                print(f"\n{len(results)} result(s)")

        else:
            segments = [FlightSegment(
                departure_airport=[[origin, 0]],
                arrival_airport=[[destination, 0]],
                travel_date=date,
            )]

            trip_type = TripType.ONE_WAY
            if is_round_trip:
                segments.append(FlightSegment(
                    departure_airport=[[destination, 0]],
                    arrival_airport=[[origin, 0]],
                    travel_date=args.return_date,
                ))
                trip_type = TripType.ROUND_TRIP

            filters = FlightSearchFilters(
                trip_type=trip_type,
                passenger_info=PassengerInfo(adults=args.adults),
                flight_segments=segments,
                seat_type=SEAT_MAP[args.cabin],
                stops=STOPS_MAP[args.stops],
            )

            print(f"Searching {orig_code} → {dest_code} on {date}...", file=sys.stderr)
            results, currency = search_with_currency(filters, top_n=args.results)

            if not results:
                print(f"  No results.", file=sys.stderr)
                continue

            # Apply post-filters
            results = filter_results(
                results,
                exclude_airlines=exclude,
                include_airlines=include,
                depart_after=args.after,
                depart_before=args.before,
                max_duration=args.max_duration,
                is_round_trip=is_round_trip,
            )

            # Sort
            if args.sort == "price":
                if is_round_trip:
                    results.sort(key=lambda x: x[0].price + x[1].price if isinstance(x, tuple) else x.price)
                else:
                    results.sort(key=lambda x: x.price)
            elif args.sort == "duration":
                if is_round_trip:
                    results.sort(key=lambda x: x[0].duration + x[1].duration if isinstance(x, tuple) else x.duration)
                else:
                    results.sort(key=lambda x: x.duration)

            results = results[:args.results]

            if args.output == "json":
                formatted = format_results(results, currency, is_round_trip)
                for f in formatted:
                    f["search"] = {"origin": orig_code, "destination": dest_code, "date": date}
                    if is_round_trip:
                        f["search"]["return_date"] = args.return_date
                all_results.extend(formatted)
            else:
                print(f"\n{'='*60}")
                print(f"{orig_code} → {dest_code} | {date} | {args.cabin} | {args.adults} pax | {currency}")
                if is_round_trip:
                    print(f"Return: {args.return_date}")
                print(format_text(results, currency, is_round_trip))
                print(f"\n{len(results)} result(s)")

    if args.output == "json":
        print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    main()
