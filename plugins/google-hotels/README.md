# Google Hotels

Search Google Hotels with **live, date-accurate pricing** — no API key, no browser automation.

## How It Works

Google Hotels uses a `ts=` URL parameter containing a protobuf-encoded blob with location + dates. This plugin reverse-engineers that protobuf format to get real-time prices via simple HTTP requests.

1. Resolves any location to a Google Maps place ID
2. Builds a protobuf `ts=` parameter encoding location + dates
3. Fetches results with live pricing (~2 seconds)
4. Parses hotel names, prices, ratings, reviews, and deals

## Features

- **Live prices** — actual rates for your dates, not cached "starting from" estimates
- **Any location** — works worldwide (NYC, Paris, Tokyo, Bali, etc.)
- **Filters** — min/max price, min rating, sort by price/rating/relevance
- **Deal detection** — flags hotels with "X% less than usual"
- **Price tracking** — monitor hotels over time for drops
- **JSON or text output**

## Usage

```bash
# Basic search
python search-hotels.py "New York City" 2026-12-31 2027-01-02

# Filter by rating and price
python search-hotels.py "Paris France" 2026-08-16 2026-08-25 --min-rating 4.0 --max-price 300

# JSON output
python search-hotels.py "Tokyo Japan" 2026-04-01 2026-04-05 -s rating -o json

# Track a hotel search for price changes
python track-hotel.py "Singapore" 2026-06-15 2026-06-18 -t 120
```

## Requirements

- Python 3
- `curl-cffi` (`pip install curl-cffi`)

## Install

```bash
bash setup.sh
```
