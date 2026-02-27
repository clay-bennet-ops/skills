---
name: hotel-search
description: >
  Search Google Hotels for hotel prices with live date-accurate pricing.
  Use when searching for hotels, comparing prices across properties,
  monitoring price drops, or planning travel accommodations. Supports
  location-based search, date ranges, rating filters, price filters,
  and price tracking with alerts.
---

# Hotel Search

Search Google Hotels with **live, date-accurate pricing** via curl. No API key needed.

## Setup

```bash
bash skills/hotel-search/setup.sh
```

Requires: Python 3, curl-cffi

## How It Works

Google Hotels uses a `ts=` URL parameter containing a protobuf-encoded blob with location + dates.
When present, prices are live and date-accurate. Without it, they're cached garbage.

The skill:
1. Fetches a Google Hotels page for the location to extract the Google Maps place ID
2. Builds a protobuf `ts=` parameter encoding the place ID + check-in/check-out dates
3. Fetches the results page with the `ts=` param → live prices
4. Parses hotel names, prices, ratings, reviews, deals from `aria-label` attributes

All via `curl_cffi` in ~2 seconds.

## Scripts

All scripts are in `skills/hotel-search/scripts/`.

### search-hotels.py — Search hotels with live prices

```bash
# Basic search
python search-hotels.py "New York City" 2026-12-31 2027-01-02

# Filter by rating and price
python search-hotels.py "Paris France" 2026-08-16 2026-08-25 --min-rating 4.0 --max-price 300

# Sort by rating, JSON output
python search-hotels.py "Tokyo Japan" 2026-04-01 2026-04-05 -s rating -o json
```

**Options:**
| Option | Description |
|--------|-------------|
| `location` | City or area (e.g. "New York City", "Paris France") |
| `checkin` | Check-in date YYYY-MM-DD |
| `checkout` | Check-out date YYYY-MM-DD |
| `-a, --adults` | Number of adults (default: 2) |
| `--min-price` | Minimum price per night |
| `--max-price` | Maximum price per night |
| `--min-rating` | Minimum guest rating (e.g. 4.0) |
| `-s, --sort` | price (default), rating, relevance |
| `-n, --results` | Max results (default: 15) |
| `-o, --output` | text (default) or json |

### track-hotel.py — Track a search for price monitoring

```bash
python track-hotel.py "New York City" 2026-03-15 2026-03-18 -t 120
```

### check-prices.py / list-tracked.py — Price tracking

```bash
python check-prices.py
python list-tracked.py
```

## Data

Price history stored in `skills/hotel-search/data/tracked.json`.

## API (search_utils.py)

```python
from search_utils import fetch_hotels, format_results_text, format_results_json

hotels = fetch_hotels("New York City", "2026-12-31", "2027-01-02", max_results=10)
# Each hotel: {name, price, rating, reviews, deal_pct, deal_type, entity_id, live_price}

print(format_results_text(hotels, "New York City", "2026-12-31", "2027-01-02"))
```
