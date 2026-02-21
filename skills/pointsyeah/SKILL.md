---
name: pointsyeah
description: Search award flights using the PointsYeah API. Use when searching for flights bookable with points/miles, comparing award availability across airlines and transfer partners (Chase UR, Bilt, Amex MR, Capital One, Citi), or finding the best redemption value for a route. Supports one-way searches by origin, destination, date, and cabin class (Economy, Premium Economy, Business, First).
metadata: {"openclaw": {"requires": {"bins": ["node"]}, "emoji": "✈️", "homepage": "https://github.com/clay-bennet-ops/pointsyeah"}}
---

# PointsYeah Award Flight Search

Search award flight availability across all major airline loyalty programs via the PointsYeah API.

## Setup

Requires a PointsYeah account. Set the refresh token:

```bash
export PY_REFRESH_TOKEN="<cognito_refresh_token>"
```

To obtain a refresh token: log into pointsyeah.com in a browser, open DevTools → Application → Local Storage → look for `CognitoIdentityServiceProvider.*.refreshToken`.

## Usage

```bash
node {baseDir}/scripts/pointsyeah-api.js \
  --departure JFK \
  --arrival CDG \
  --departDate 2026-08-15 \
  --cabins "Premium Economy,Business"
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--departure` | Yes | Origin airport or metro code | `JFK`, `NYC`, `LAX` |
| `--arrival` | Yes | Destination airport or metro code | `CDG`, `NRT`, `LHR` |
| `--departDate` | Yes | Date in YYYY-MM-DD format | `2026-08-15` |
| `--cabins` | No | Comma-separated cabin classes | `"Business"`, `"Premium Economy,Business"` |
| `--adults` | No | Number of adults (default: 1) | `2` |

### Metro Codes

Use metro codes (e.g. `NYC`, `LON`, `TYO`) to search all airports in a metro area simultaneously.

## Output

Outputs JSON array to stdout (mixed with log lines to stderr). Each result contains:

```json
{
  "program": "Air France-KLM Flying Blue",
  "code": "AF",
  "date": "2026-08-15",
  "departure": "JFK",
  "arrival": "CDG",
  "routes": [{
    "payment": {
      "miles": 85000,
      "tax": 372.00,
      "cabin": "Business",
      "seats": 9
    },
    "segments": [{
      "flight_number": "AF0005",
      "da": "JFK", "aa": "CDG",
      "dt": "2026-08-15T18:00:00",
      "duration": 445,
      "cabin": "Business",
      "aircraft": "Boeing 777-300ER"
    }],
    "duration": 445,
    "transfer": [{
      "bank": "Chase Ultimate Rewards",
      "points": 85000,
      "bonus_percentage": 0
    }, {
      "bank": "Bilt Rewards",
      "points": 85000,
      "bonus_percentage": 0
    }]
  }]
}
```

Key fields in `routes[].transfer[]`:
- `bank` — Transfer partner bank name
- `points` — Points needed from that bank (after any transfer bonus)
- `bonus_percentage` — Active transfer bonus (e.g. 40 = 40% bonus)
- `bonus_end_date` — When the bonus expires

## Rate Limiting

- **Wait 20-30 seconds between searches** to avoid HTTP 429 errors
- Each search takes ~15-25 seconds (creates task, polls ~5-8 times at 3s intervals)
- If you get a 429, wait 60 seconds before retrying
- Token refresh happens automatically per search (Cognito tokens valid ~1 hour)

## Batch Searching Tips

For scanning many routes, run sequentially with delays:

```bash
for CITY in CDG FCO LHR; do
  for DAY in 15 16 17 18; do
    node {baseDir}/scripts/pointsyeah-api.js \
      --departure NYC --arrival $CITY \
      --departDate "2026-08-$DAY" \
      --cabins "Premium Economy,Business" \
      > "/tmp/search_${CITY}_aug${DAY}.json" 2>&1
    sleep 25
  done
done
```

## Parsing Results

To extract only transferable options from output files (which contain log lines + JSON):

```javascript
const raw = fs.readFileSync(file, 'utf8');
const jsonStart = raw.indexOf('[\n  {');
if (jsonStart === -1) return; // no results
const results = JSON.parse(raw.slice(jsonStart).trim());

for (const r of results) {
  for (const route of r.routes || []) {
    const chase = route.transfer?.find(t => t.bank === 'Chase Ultimate Rewards');
    const bilt = route.transfer?.find(t => t.bank === 'Bilt Rewards');
    // Filter by cabin, bank, stops, duration as needed
  }
}
```

## Common Transfer Partners

| Bank | Key Partners |
|------|-------------|
| Chase UR | United, Virgin Atlantic, Air France/KLM, BA, Singapore, Aeroplan, Hyatt |
| Bilt | United, Virgin Atlantic, Air France/KLM, BA, Turkish, AA, Alaska, Aeroplan, TAP |
| Amex MR | Delta, ANA, BA, Etihad, Singapore, Air France/KLM, Aeroplan |
| Capital One | Air France/KLM, BA, Turkish, Etihad, Singapore, Avianca, Finnair |
