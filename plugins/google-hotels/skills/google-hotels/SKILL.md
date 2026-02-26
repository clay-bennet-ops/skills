---
name: hotel-search
description: >
  Search Google Hotels for hotel prices and track price changes over time.
  Use when searching for hotels, comparing prices across properties,
  monitoring price drops, or planning travel accommodations. Supports
  location-based search, date ranges, rating filters, price filters,
  and price tracking with alerts.
---

# Hotel Search

Search Google Hotels and track prices. No API key needed.

## Setup

```bash
bash skills/hotel-search/setup.sh
```

Requires: Python 3, curl-cffi

## Scripts

All scripts are in `skills/hotel-search/scripts/`. Run from that directory.

### search-hotels.py — Search hotels

```bash
# Basic search
python search-hotels.py "New York City" 2026-03-15 2026-03-18

# Filter by rating and price
python search-hotels.py "Paris France" 2026-08-16 2026-08-25 --min-rating 4.0 --max-price 300

# Sort by rating, JSON output
python search-hotels.py "Miami Beach" 2026-06-01 2026-06-05 -s rating -o json

# Budget search
python search-hotels.py "Tokyo" 2026-04-01 2026-04-07 --max-price 150 -n 20
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
| `--currency` | Currency code (default: USD) |

**JSON output** includes search metadata, hotel name, price per night, rating, review count, and deal info.

### track-hotel.py — Track a search for price monitoring

```bash
# Track NYC hotels with a target price
python track-hotel.py "New York City" 2026-03-15 2026-03-18 -t 120

# Track a specific hotel
python track-hotel.py "Paris France" 2026-08-16 2026-08-25 --hotel-name "Hotel Le Marais"
```

### check-prices.py — Check all tracked hotels (cron-ready)

```bash
# Check all tracked searches
python check-prices.py

# Alert on 5% drops (default: 10%)
python check-prices.py --threshold 5

# JSON output for automated processing
python check-prices.py --json
```

### list-tracked.py — Show tracked searches

```bash
python list-tracked.py
```

## Data

Price history stored in `skills/hotel-search/data/tracked.json`.

## Notes

- Uses curl_cffi to scrape Google Hotels (no API key needed)
- Prices are per night per room
- Ratings are guest ratings (out of 5), not star class
- Deal info shows percentage below typical price
- Results limited to what Google returns on first page (~20-40 hotels)
- For best results, use specific location names ("Manhattan NYC" vs "New York")
