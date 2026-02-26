#!/usr/bin/env python3
"""Check prices for all tracked hotel searches. Cron-ready."""

import argparse
import json
import os
import sys
from datetime import datetime

from search_utils import fetch_hotels

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TRACKED_FILE = os.path.join(DATA_DIR, "tracked.json")


def load_tracked():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE) as f:
            return json.load(f)
    return []


def save_tracked(tracked):
    with open(TRACKED_FILE, "w") as f:
        json.dump(tracked, f, indent=2)


def parse_args():
    p = argparse.ArgumentParser(description="Check tracked hotel prices")
    p.add_argument("--threshold", type=int, default=10,
                   help="Alert on price drops of N%% or more (default: 10)")
    p.add_argument("--json", action="store_true", help="JSON output")
    return p.parse_args()


def main():
    args = parse_args()
    tracked = load_tracked()
    
    if not tracked:
        print("No tracked hotel searches. Use track-hotel.py to add one.")
        return
    
    alerts = []
    
    for i, entry in enumerate(tracked):
        location = entry["location"]
        checkin = entry["checkin"]
        checkout = entry["checkout"]
        
        # Skip past dates
        if datetime.strptime(checkin, "%Y-%m-%d").date() < datetime.now().date():
            continue
        
        print(f"Checking {location} ({checkin} → {checkout})...", file=sys.stderr)
        
        try:
            hotels = fetch_hotels(
                location=location,
                checkin=checkin,
                checkout=checkout,
                adults=entry.get("adults", 2),
                min_rating=entry.get("min_rating"),
                max_price=entry.get("max_price"),
                sort_by="price",
                max_results=10,
            )
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            continue
        
        if not hotels:
            continue
        
        # If tracking specific hotel
        hotel_name_filter = entry.get("hotel_name")
        if hotel_name_filter:
            hotels = [h for h in hotels if hotel_name_filter.lower() in h['name'].lower()]
        
        # Get cheapest
        cheapest = min(hotels, key=lambda x: x.get('price', 9999)) if hotels else None
        if not cheapest or 'price' not in cheapest:
            continue
        
        current_price = cheapest['price']
        now = datetime.now().isoformat()
        
        # Record price history
        entry.setdefault("price_history", []).append({
            "date": now,
            "price": current_price,
            "hotel": cheapest['name'],
        })
        
        # Keep last 100 entries
        entry["price_history"] = entry["price_history"][-100:]
        
        # Check for alerts
        target = entry.get("target_price")
        if target and current_price <= target:
            alerts.append({
                "type": "target_hit",
                "location": location,
                "dates": f"{checkin} → {checkout}",
                "hotel": cheapest['name'],
                "price": current_price,
                "target": target,
            })
        
        # Check for price drops vs previous
        history = entry["price_history"]
        if len(history) >= 2:
            prev_price = history[-2]["price"]
            if prev_price > 0:
                drop_pct = (prev_price - current_price) / prev_price * 100
                if drop_pct >= args.threshold:
                    alerts.append({
                        "type": "price_drop",
                        "location": location,
                        "dates": f"{checkin} → {checkout}",
                        "hotel": cheapest['name'],
                        "price": current_price,
                        "prev_price": prev_price,
                        "drop_pct": round(drop_pct, 1),
                    })
    
    save_tracked(tracked)
    
    if args.json:
        print(json.dumps({"alerts": alerts, "checked": len(tracked)}))
    else:
        if alerts:
            print(f"\n🏨 Hotel Price Alerts ({len(alerts)}):")
            for a in alerts:
                if a["type"] == "target_hit":
                    print(f"  🎯 {a['location']}: ${a['price']}/nt at {a['hotel']} (target: ${a['target']})")
                elif a["type"] == "price_drop":
                    print(f"  📉 {a['location']}: ${a['price']}/nt at {a['hotel']} (was ${a['prev_price']}, -{a['drop_pct']}%)")
                print(f"     {a['dates']}")
        else:
            print("No alerts. All prices stable.")


if __name__ == "__main__":
    main()
