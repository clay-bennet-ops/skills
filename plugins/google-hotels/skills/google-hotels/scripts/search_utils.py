"""Shared utilities for hotel search scripts."""

import base64
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


# ─── Protobuf encoding for the `ts=` URL parameter ───

def _encode_varint(value):
    """Encode an integer as a protobuf varint."""
    result = []
    while value > 0x7f:
        result.append((value & 0x7f) | 0x80)
        value >>= 7
    result.append(value & 0x7f)
    return bytes(result)


def _make_date_bytes(year, month, day):
    """Encode a date as protobuf fields: field1=year, field2=month, field3=day."""
    return b'\x08' + _encode_varint(year) + b'\x10' + _encode_varint(month) + b'\x18' + _encode_varint(day)



def _build_ts_from_location(location, checkin_date, checkout_date, currency="USD"):
    """Build ts= param by resolving location to a Google Maps place ID, then constructing protobuf.
    
    Google never returns ts= in server responses — it's generated client-side.
    So we extract the place ID and location name from the page, then build the protobuf from scratch.
    """
    if not HAS_CURL_CFFI:
        raise ImportError("curl_cffi required")
    
    # Fetch a Google Hotels/Travel page for this location to extract the place ID
    url = f"https://www.google.com/travel/hotels?q=hotels+in+{urllib.parse.quote(location)}&hl=en&gl=us"
    resp = curl_requests.get(url, impersonate="chrome", timeout=20)
    if resp.status_code != 200:
        raise Exception(f"Failed to resolve location: status {resp.status_code}")
    
    # Extract place ID (format: 0x<hex>:0x<hex>)
    loc_match = re.search(r'(0x[0-9a-f]+:0x[0-9a-f]+)', resp.text)
    if not loc_match:
        raise Exception(f"Could not extract place ID for '{location}'")
    
    place_id = loc_match.group(1)
    
    # Extract location display name from data blocks near the place ID
    # Google embeds it as: place_id","LocationName"
    name_match = re.search(
        re.escape(place_id) + r'","([^"]{2,50})"',
        resp.text
    )
    if name_match:
        loc_name = name_match.group(1)
    else:
        # Fallback: use the input location name (simplified)
        loc_name = location.split(',')[0].strip()
    
    return _build_ts_protobuf(place_id, loc_name, checkin_date, checkout_date, currency)


def _build_ts_protobuf(place_id, location_name, checkin_date, checkout_date, currency="USD"):
    """Build the ts= protobuf from scratch given a place ID and dates.
    
    Protobuf structure (reverse-engineered):
    field 1 (varint): 1
    field 2 (bytes): nested {field1: {field1: 3}, field1: {field1: 3}, field2: 0}
    field 3 (bytes): nested {
        field1: {field2: {field6: place_id, field7: location_name}},  -- location
        field1: {empty},  -- unused
        field2: {field2: {field1: checkin_date, field2: checkout_date, field3: 2}, field6: {field1: 1}}  -- dates + guests
    }
    field 5 (bytes): nested {field1: {field7: currency}, field3: {empty}}  -- currency
    """
    cin = datetime.strptime(checkin_date, "%Y-%m-%d")
    cout = datetime.strptime(checkout_date, "%Y-%m-%d")
    
    # Helper to build length-delimited field
    def field_ld(field_num, data):
        tag = (field_num << 3) | 2
        return bytes([tag]) + _encode_varint(len(data)) + data
    
    def field_vi(field_num, value):
        tag = (field_num << 3) | 0
        return bytes([tag]) + _encode_varint(value)
    
    def field_str(field_num, s):
        encoded = s.encode('utf-8')
        return field_ld(field_num, encoded)
    
    # Date bytes
    cin_date = field_vi(1, cin.year) + field_vi(2, cin.month) + field_vi(3, cin.day)
    cout_date = field_vi(1, cout.year) + field_vi(2, cout.month) + field_vi(3, cout.day)
    
    # Location: field2 > field6=place_id, field7=name
    # The place_id is URL-encoded in the protobuf
    # Place ID goes into protobuf as-is (with colons), NOT URL-encoded
    location_inner = field_str(6, place_id) + field_str(7, location_name)
    location_block = field_ld(2, location_inner)
    
    # Dates block: field2 > field1=checkin, field2=checkout, field3=2(adults)
    dates_inner = field_ld(1, cin_date) + field_ld(2, cout_date) + field_vi(3, 2)
    guests_block = field_ld(6, field_vi(1, 1))
    dates_block = field_ld(2, dates_inner) + guests_block
    
    # Field 3: location + dates
    f3 = field_ld(1, location_block) + field_ld(3, b'') + field_ld(2, dates_block)
    
    # Field 2: room config {field1:{field1:3}, field1:{field1:3}, field2:0}
    room_inner = field_ld(1, field_vi(1, 3)) + field_ld(1, field_vi(1, 3)) + field_vi(2, 0)
    
    # Field 5: currency
    currency_inner = field_ld(1, field_str(7, currency)) + field_ld(3, b'')
    
    # Full message
    msg = field_vi(1, 1) + field_ld(2, room_inner) + field_ld(3, f3) + field_ld(5, currency_inner)
    
    return base64.urlsafe_b64encode(msg).rstrip(b'=').decode()



# ─── Main search functions ───

def build_search_url(location, checkin, checkout, adults=2, sort_by="price", currency="USD"):
    """Build a Google Hotels search URL with live pricing via ts= protobuf param."""
    sort_map = {"relevance": "MAA", "price": "MAE", "rating": "MAI", "distance": "MAC"}
    ap = sort_map.get(sort_by, "MAE")
    
    try:
        ts = _build_ts_from_location(location, checkin, checkout, currency)
        params = {
            "q": f"hotels in {location}",
            "qs": "CAE4AA",
            "hl": "en",
            "gl": "us",
            "ts": ts,
            "ap": ap,
        }
    except Exception:
        # Fallback to basic URL (will return cached prices)
        params = {
            "q": f"hotels in {location}",
            "hl": "en",
            "gl": "us",
            "checkin": checkin,
            "checkout": checkout,
            "currency": currency,
            "ap": ap,
        }
    
    return "https://www.google.com/travel/search?" + urllib.parse.urlencode(params)


def fetch_hotels(location, checkin, checkout, adults=2, min_price=None, max_price=None,
                 min_rating=None, sort_by="price", max_results=20, currency="USD"):
    """Fetch hotel results with LIVE date-accurate prices.
    
    Uses the ts= protobuf URL parameter to get date-specific pricing from Google Hotels.
    Falls back to cached prices if location resolution fails.
    """
    if not HAS_CURL_CFFI:
        raise ImportError("curl_cffi required. Install with: pip3 install curl-cffi")
    
    url = build_search_url(location, checkin, checkout, adults, sort_by=sort_by, currency=currency)
    
    resp = curl_requests.get(url, impersonate="chrome", timeout=20)
    if resp.status_code != 200:
        raise Exception(f"Google Hotels returned status {resp.status_code}")
    
    # Check if we got live prices (dates in inputs match requested dates)
    live = "qs=CAE4AA" in resp.url or "ts=" in resp.url
    
    hotels = parse_hotel_results(resp.text)
    
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
    
    for h in hotels:
        h['live_price'] = live
    
    return hotels[:max_results]


def parse_hotel_results(html):
    """Parse hotel results from Google Hotels HTML aria-labels."""
    hotels = {}
    
    price_labels = re.findall(
        r'Prices starting from \\?\$([\d,]+),\s*(.+?)(?:\s+(?:DEAL|GREAT DEAL)\s+(\d+)% less than usual)?\s*"',
        html
    )
    for price_str, name, deal_pct in price_labels:
        name = clean_name(name)
        if not name:
            continue
        price = int(price_str.replace(',', ''))
        if name not in hotels:
            hotels[name] = {'name': name, 'price': price}
        if deal_pct:
            hotels[name]['deal_pct'] = int(deal_pct)
            hotels[name]['deal_type'] = 'GREAT DEAL' if int(deal_pct) >= 30 else 'DEAL'
    
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
    
    star_labels = re.findall(r'(\d)-star\s+hotel[^"]*?,\s*([^"]+?)"', html, re.IGNORECASE)
    for stars, name in star_labels:
        name = clean_name(name)
        if name in hotels:
            hotels[name]['star_class'] = int(stars)
    
    # Extract entity IDs
    entity_pattern = re.findall(
        r'aria-label="([^"]+)"[^>]*data-suffix=""[^>]*href="[^"]*entity/([^?&"]+)',
        html
    )
    for label, entity_id in entity_pattern:
        name = clean_name(label)
        if name in hotels:
            hotels[name]['entity_id'] = entity_id
    
    # Filter garbage
    valid = []
    for h in hotels.values():
        name = h.get('name', '')
        price = h.get('price', 0)
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
    name = name.replace('&amp;', '&').replace('&#39;', "'").replace('&quot;', '"')
    name = name.rstrip(' ,.')
    return name if len(name) > 2 else None


def format_results_json(hotels, location, checkin, checkout, adults=2, live=None):
    """Format hotel results as JSON."""
    nights = (datetime.strptime(checkout, "%Y-%m-%d") - datetime.strptime(checkin, "%Y-%m-%d")).days
    if live is None:
        live = hotels[0].get('live_price', False) if hotels else False
    return {
        "search": {
            "location": location,
            "checkin": checkin,
            "checkout": checkout,
            "nights": nights,
            "adults": adults,
            "price_type": "live" if live else "cached",
        },
        "results": hotels,
        "count": len(hotels),
    }


def format_results_text(hotels, location, checkin, checkout, adults=2, live=None):
    """Format hotel results as human-readable text."""
    nights = (datetime.strptime(checkout, "%Y-%m-%d") - datetime.strptime(checkin, "%Y-%m-%d")).days
    if live is None:
        live = hotels[0].get('live_price', False) if hotels else False
    
    lines = []
    lines.append(f"Hotels in {location}")
    lines.append(f"Check-in: {checkin} | Check-out: {checkout} ({nights} night{'s' if nights != 1 else ''})")
    if not live:
        lines.append(f"⚠️  Prices are cached/approximate")
    lines.append(f"{'='*65}")
    
    for i, h in enumerate(hotels, 1):
        price = f"${h['price']:,}/nt" if 'price' in h else "N/A"
        total = f"(${h['price'] * nights:,} total)" if 'price' in h else ""
        rating = f"{h['rating']}★" if 'rating' in h else ""
        reviews = f"({h.get('reviews', '?'):,} reviews)" if 'rating' in h else ""
        deal = f" 🏷️ {h['deal_pct']}% off" if 'deal_pct' in h else ""
        star_class = f" [{h['star_class']}⭐]" if 'star_class' in h else ""
        
        lines.append(f"\n{i:2d}. {h['name']}{star_class}")
        lines.append(f"    {price} {total}  {rating} {reviews}{deal}")
    
    lines.append(f"\n{len(hotels)} results")
    return "\n".join(lines)
