#!/usr/bin/env python3
"""Track a hotel search for price monitoring."""

import argparse
import json
import os
import sys
from datetime import datetime

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
    p = argparse.ArgumentParser(description="Track hotel prices")
    p.add_argument("location", help="City or area")
    p.add_argument("checkin", help="Check-in date (YYYY-MM-DD)")
    p.add_argument("checkout", help="Check-out date (YYYY-MM-DD)")
    p.add_argument("--adults", "-a", type=int, default=2)
    p.add_argument("--target", "-t", type=int, help="Target price per night (alert when below)")
    p.add_argument("--min-rating", type=float, help="Minimum rating filter")
    p.add_argument("--max-price", type=int, help="Max price per night filter")
    p.add_argument("--hotel-name", help="Track a specific hotel by name (partial match)")
    return p.parse_args()


def main():
    args = parse_args()
    tracked = load_tracked()
    
    entry = {
        "location": args.location,
        "checkin": args.checkin,
        "checkout": args.checkout,
        "adults": args.adults,
        "target_price": args.target,
        "min_rating": args.min_rating,
        "max_price": args.max_price,
        "hotel_name": args.hotel_name,
        "created": datetime.now().isoformat(),
        "price_history": [],
    }
    
    tracked.append(entry)
    save_tracked(tracked)
    
    print(f"Tracking hotels in {args.location}")
    print(f"  {args.checkin} → {args.checkout}, {args.adults} adults")
    if args.target:
        print(f"  Alert when price drops below ${args.target}/night")
    if args.hotel_name:
        print(f"  Tracking specific hotel: {args.hotel_name}")
    print(f"\nTotal tracked searches: {len(tracked)}")


if __name__ == "__main__":
    main()
