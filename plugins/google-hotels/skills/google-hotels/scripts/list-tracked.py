#!/usr/bin/env python3
"""Show tracked hotel searches and their price history."""

import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TRACKED_FILE = os.path.join(DATA_DIR, "tracked.json")


def main():
    if not os.path.exists(TRACKED_FILE):
        print("No tracked hotel searches.")
        return
    
    with open(TRACKED_FILE) as f:
        tracked = json.load(f)
    
    if not tracked:
        print("No tracked hotel searches.")
        return
    
    print(f"Tracked Hotel Searches ({len(tracked)}):")
    print("=" * 60)
    
    for i, entry in enumerate(tracked, 1):
        location = entry["location"]
        checkin = entry["checkin"]
        checkout = entry["checkout"]
        adults = entry.get("adults", 2)
        target = entry.get("target_price")
        hotel = entry.get("hotel_name")
        history = entry.get("price_history", [])
        
        print(f"\n{i}. {location}")
        print(f"   {checkin} → {checkout}, {adults} adults")
        if target:
            print(f"   Target: ${target}/night")
        if hotel:
            print(f"   Tracking: {hotel}")
        
        if history:
            latest = history[-1]
            print(f"   Latest: ${latest['price']}/nt at {latest['hotel']} ({latest['date'][:10]})")
            if len(history) > 1:
                prices = [h['price'] for h in history]
                print(f"   Range: ${min(prices)} - ${max(prices)} ({len(history)} checks)")


if __name__ == "__main__":
    main()
