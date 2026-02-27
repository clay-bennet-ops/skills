#!/usr/bin/env python3
"""Search Google Hotels for a location and dates. Outputs JSON or text.

Uses protobuf-encoded ts= parameter for live, date-accurate pricing via curl.
"""

import argparse
import json
import sys

from search_utils import fetch_hotels, format_results_json, format_results_text


def parse_args():
    p = argparse.ArgumentParser(description="Search Google Hotels")
    p.add_argument("location", help="City or area (e.g. 'New York City', 'Paris France', 'Miami Beach')")
    p.add_argument("checkin", help="Check-in date (YYYY-MM-DD)")
    p.add_argument("checkout", help="Check-out date (YYYY-MM-DD)")
    p.add_argument("--adults", "-a", type=int, default=2, help="Number of adults (default: 2)")
    p.add_argument("--min-price", type=int, help="Minimum price per night")
    p.add_argument("--max-price", type=int, help="Maximum price per night")
    p.add_argument("--min-rating", type=float, help="Minimum guest rating (e.g. 4.0)")
    p.add_argument("--sort", "-s", default="price", choices=["price", "rating", "relevance"],
                   help="Sort by (default: price)")
    p.add_argument("--results", "-n", type=int, default=15, help="Max results (default: 15)")
    p.add_argument("--output", "-o", default="text", choices=["json", "text"], help="Output format")
    p.add_argument("--currency", default="USD", help="Currency code (default: USD)")
    return p.parse_args()


def main():
    args = parse_args()
    
    print(f"Searching hotels in {args.location}...", file=sys.stderr)
    print(f"  {args.checkin} → {args.checkout}, {args.adults} adults", file=sys.stderr)
    
    try:
        hotels = fetch_hotels(
            location=args.location,
            checkin=args.checkin,
            checkout=args.checkout,
            adults=args.adults,
            min_price=args.min_price,
            max_price=args.max_price,
            min_rating=args.min_rating,
            sort_by=args.sort,
            max_results=args.results,
            currency=args.currency,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not hotels:
        print("No hotels found matching your criteria.", file=sys.stderr)
        sys.exit(0)
    
    print(f"  Found {len(hotels)} hotels", file=sys.stderr)
    
    if args.output == "json":
        data = format_results_json(hotels, args.location, args.checkin, args.checkout, args.adults)
        print(json.dumps(data, indent=2))
    else:
        print(format_results_text(hotels, args.location, args.checkin, args.checkout, args.adults))


if __name__ == "__main__":
    main()
