"""Shared utilities for hotel search scripts."""

import hashlib
import hmac
import json
import os
import re
import urllib.parse
from datetime import datetime

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

PREFS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "preferences.json")

def _load_prefs():
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE) as f:
            return json.load(f)
    return {}

PREFS = _load_prefs()

# Star rating filter presets
STAR_PRESETS = {
    "budget": (0, 3),
    "mid": (3, 4),
    "upscale": (4, 5),
    "luxury": (4.5, 5),
}


def build_search_url(location, checkin, checkout, adults=2, min_price=None, max_price=None,
                     star_rating=None, sort_by="price", currency="USD"):
    """Build a Google Hotels search URL with parameters."""
    params = {
        "q": f"hotels in {location}",
        "hl": "en",
        "gl": "us",
        "checkin": checkin,
        "checkout": checkout,
        "currency": currency,
    }
    
    # Sort: MAA = relevance, MAE = price low-high, MAI = rating
    sort_map = {
        "relevance": "MAA",
        "price": "MAE",
        "rating": "MAI",
        "distance": "MAC",
    }
    params["ap"] = sort_map.get(sort_by, "MAE")
    
    url = "https://www.google.com/travel/hotels?" + urllib.parse.urlencode(params)
    return url


def fetch_hotels(location, checkin, checkout, adults=2, min_price=None, max_price=None,
                 min_rating=None, sort_by="price", max_results=20, currency="USD"):
    """Fetch hotel results from Google Hotels."""
    if not HAS_CURL_CFFI:
        raise ImportError("curl_cffi required. Install with: pip3 install curl-cffi")
    
    url = build_search_url(location, checkin, checkout, adults, sort_by=sort_by, currency=currency)
    
    resp = curl_requests.get(url, impersonate="chrome", timeout=20)
    if resp.status_code != 200:
        raise Exception(f"Google Hotels returned status {resp.status_code}")
    
    html = resp.text
    hotels = parse_hotel_results(html)
    
    # Apply filters
    if min_price is not None:
        hotels = [h for h in hotels if h.get('price', 0) >= min_price]
    if max_price is not None:
        hotels = [h for h in hotels if h.get('price', 9999) <= max_price]
    if min_rating is not None:
        hotels = [h for h in hotels if h.get('rating', 0) >= min_rating]
    
    # Sort
    if sort_by == "price":
        hotels.sort(key=lambda x: x.get('price', 9999))
    elif sort_by == "rating":
        hotels.sort(key=lambda x: -x.get('rating', 0))
    
    return hotels[:max_results]


def parse_hotel_results(html):
    """Parse hotel results from Google Hotels HTML."""
    hotels = {}
    
    # Extract prices from aria-labels
    # Pattern: "Prices starting from $XXX, HOTEL_NAME [DEAL info]"
    price_labels = re.findall(
        r'Prices starting from \$(\d+),\s*(.+?)(?:\s+(?:DEAL|GREAT DEAL)\s+\d+% less than usual)?"',
        html
    )
    for price, name in price_labels:
        name = clean_name(name)
        if name and name not in hotels:
            hotels[name] = {'name': name, 'price': int(price)}
    
    # Extract ratings
    # Pattern: "X.X out of 5 stars from N reviews, HOTEL_NAME"
    rating_labels = re.findall(
        r'(\d\.\d) out of 5 stars from ([\d,]+) reviews?,\s*([^"]+?)"',
        html
    )
    for rating, reviews, name in rating_labels:
        name = clean_name(name)
        if name in hotels:
            hotels[name]['rating'] = float(rating)
            hotels[name]['reviews'] = int(reviews.replace(',', ''))
        elif name:
            hotels[name] = {
                'name': name,
                'rating': float(rating),
                'reviews': int(reviews.replace(',', '')),
            }
    
    # Extract deal info
    deal_labels = re.findall(
        r'Prices starting from \$(\d+),\s*(.+?)\s+((?:GREAT )?DEAL)\s+(\d+)% less than usual',
        html
    )
    for price, name, deal_type, pct in deal_labels:
        name = clean_name(name)
        if name in hotels:
            hotels[name]['deal_pct'] = int(pct)
            hotels[name]['deal_type'] = deal_type.strip()
    
    # Extract star class (hotel class)
    # Sometimes available as "N-star hotel" in aria-labels
    star_labels = re.findall(r'(\d)-star\s+hotel[^"]*?,\s*([^"]+?)"', html, re.IGNORECASE)
    for stars, name in star_labels:
        name = clean_name(name)
        if name in hotels:
            hotels[name]['star_class'] = int(stars)
    
    # Filter out garbage entries (too short names, $0-1 prices, numeric-only names)
    valid = []
    for h in hotels.values():
        name = h.get('name', '')
        price = h.get('price', 0)
        # Skip entries with very short names, numeric-only names, or $0-1 prices
        if len(name) < 5:
            continue
        if re.match(r'^[\d\s,]+$', name):
            continue
        if price <= 1:
            continue
        valid.append(h)
    
    return valid


def clean_name(name):
    """Clean hotel name string."""
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)
    # Decode HTML entities
    name = name.replace('&amp;', '&')
    name = name.replace('&#39;', "'")
    name = name.replace('&quot;', '"')
    # Remove trailing whitespace/punctuation
    name = name.rstrip(' ,.')
    return name if len(name) > 2 else None


def format_results_json(hotels, location, checkin, checkout, adults=2):
    """Format hotel results as JSON."""
    nights = (datetime.strptime(checkout, "%Y-%m-%d") - datetime.strptime(checkin, "%Y-%m-%d")).days
    return {
        "search": {
            "location": location,
            "checkin": checkin,
            "checkout": checkout,
            "nights": nights,
            "adults": adults,
        },
        "results": hotels,
        "count": len(hotels),
    }


def format_results_text(hotels, location, checkin, checkout, adults=2):
    """Format hotel results as human-readable text."""
    nights = (datetime.strptime(checkout, "%Y-%m-%d") - datetime.strptime(checkin, "%Y-%m-%d")).days
    
    lines = []
    lines.append(f"Hotels in {location}")
    lines.append(f"Check-in: {checkin} | Check-out: {checkout} ({nights} night{'s' if nights != 1 else ''})")
    lines.append(f"{'='*65}")
    
    for i, h in enumerate(hotels, 1):
        price = f"${h['price']}/nt" if 'price' in h else "N/A"
        total = f"(${h['price'] * nights} total)" if 'price' in h else ""
        rating = f"{h['rating']}★" if 'rating' in h else ""
        reviews = f"({h.get('reviews', '?'):,} reviews)" if 'rating' in h else ""
        deal = f" 🏷️ {h['deal_pct']}% off" if 'deal_pct' in h else ""
        star_class = f" [{h['star_class']}⭐]" if 'star_class' in h else ""
        
        lines.append(f"\n{i:2d}. {h['name']}{star_class}")
        lines.append(f"    {price} {total}  {rating} {reviews}{deal}")
    
    lines.append(f"\n{len(hotels)} results")
    return "\n".join(lines)
