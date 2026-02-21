# PointsYeah

Search award flights bookable with points/miles across all major loyalty programs.

Works with **Claude Code**, **Claude Cowork**, and **OpenClaw**.

## Features

- Search any origin/destination pair for award availability
- All major transfer partners: Chase UR, Bilt, Amex MR, Capital One, Citi
- Shows exact points needed from each bank (including active transfer bonuses)
- Supports Economy, Premium Economy, Business, and First class
- Metro code support (NYC, LON, TYO, etc.)

## Install

### Claude Code / Cowork
```bash
claude --plugin-dir ./pointsyeah
```
Then use: `/pointsyeah:pointsyeah JFK to CDG on 2026-08-15 in Business`

### OpenClaw
Copy `skills/pointsyeah/` to your workspace `skills/` directory.

## Setup

Requires a PointsYeah account. Get your refresh token:

1. Log into pointsyeah.com in a browser
2. Open DevTools → Application → Local Storage
3. Find `CognitoIdentityServiceProvider.*.refreshToken`
4. Set it: `export PY_REFRESH_TOKEN="<token>"`

## Usage

```bash
node skills/pointsyeah/scripts/pointsyeah-api.js \
  --departure JFK \
  --arrival CDG \
  --departDate 2026-08-15 \
  --cabins "Premium Economy,Business"
```

## Rate Limiting

Wait 20-30 seconds between searches to avoid 429 errors.

## License

MIT
