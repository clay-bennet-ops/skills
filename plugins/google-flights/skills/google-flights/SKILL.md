---
name: google-flights
description: >
  Search Google Flights for cash flight prices and track price changes over time.
  Use when searching for flights, comparing prices across airlines and airports,
  monitoring price drops, or planning travel. Supports multi-airport searches,
  round trips, airline filtering, time windows, and price tracking with alerts.
  Spirit and Frontier are excluded by default.
---

# Flight Search

Search Google Flights and track prices. No API key needed.

## Setup

```bash
bash skills/google-flights/setup.sh
```

Requires: Python 3, pip

## Scripts

All scripts are in `skills/google-flights/scripts/`. Run from that directory.

### search-flights.py — Search flights

```bash
# Basic one-way
python search-flights.py JFK MIA 2026-03-19

# Round trip, 2 adults, evening flights only
python search-flights.py JFK,EWR,LGA MIA 2026-03-19 -r 2026-03-22 -a 2 --after 17

# Business class, nonstop only
python search-flights.py JFK CDG 2026-08-16 -c business -s nonstop

# Separate tickets (searches each direction as one-way, finds cheaper combos)
python search-flights.py JFK MIA 2026-03-19 -r 2026-03-22 --separate

# Date range scan
python search-flights.py JFK MIA 2026-03-18 --date-to 2026-03-21

# Text output instead of JSON
python search-flights.py JFK MIA 2026-03-19 -o text

# Include only specific airlines
python search-flights.py JFK MIA 2026-03-19 --include AA,DL,UA

# Allow Spirit/Frontier (excluded by default)
python search-flights.py JFK MIA 2026-03-19 --no-exclude
```

**Options:**
| Option | Description |
|--------|-------------|
| `origin` | Airport(s), comma-separated (e.g. JFK,EWR,LGA) |
| `destination` | Airport(s), comma-separated |
| `date` | Departure date YYYY-MM-DD |
| `--date-to` | End of date range (searches each day) |
| `-r, --return-date` | Return date for round trips |
| `-a, --adults` | Number of adults (default: 1) |
| `-c, --cabin` | economy, premium, business, first |
| `-s, --stops` | any, nonstop, 1, 2 |
| `-n, --results` | Max results (default: 10) |
| `--exclude` | Exclude airlines by IATA code (default: NK,F9) |
| `--no-exclude` | Don't exclude any airlines |
| `--include` | Only show these airlines |
| `--after` | Depart after hour (24h format, e.g. 17) |
| `--before` | Depart before hour |
| `--max-duration` | Max duration in minutes |
| `-o, --output` | json (default) or text |
| `--separate` | Search each direction as one-way, combine cheapest (⚠️ see warning below) |
| `--sort` | price (default), duration, stops |

**JSON output** includes full leg details for both outbound and return flights.

### track-flight.py — Track a route for price monitoring

```bash
# Track NYC→MIA Eid weekend
python track-flight.py JFK,EWR,LGA MIA 2026-03-19 -r 2026-03-22 -a 2 -t 400

# Track with target price alert
python track-flight.py JFK CDG 2026-08-16 -r 2026-08-25 -t 600
```

### check-prices.py — Check all tracked flights (cron-ready)

```bash
# Check all tracked flights
python check-prices.py

# Alert on 5% drops (default: 10%)
python check-prices.py --threshold 5

# JSON output for automated processing
python check-prices.py --json
```

### list-tracked.py — Show tracked flights

```bash
python list-tracked.py
```

## ⚠️ IMPORTANT: Always Search Both Modes

**For any round-trip search, you MUST run both a bundled search (`-r`) AND a separate search (`--separate`) unless the user explicitly says not to.** Google Flights often finds significantly cheaper fares by combining two one-way tickets. If you only run bundled, you may miss the best price.

Present both results clearly, noting which is bundled vs separate tickets. Separate tickets mean:
- No rebooking protection if one leg is cancelled
- Separate check-ins / bags won't auto-transfer
- Price of second leg can change before you book it

## Data

Price history stored in `skills/google-flights/data/tracked.json`.

## Notes

- Uses the `fli` library (Google Flights protobuf scraper)
- Spirit (NK) and Frontier (F9) excluded by default
- Prices are per-person for one-way, total for round-trip
- Times shown in local airport timezone
- Multi-airport searches check all origin×destination combinations
- Round-trip searches pair outbound+return options with total prices
