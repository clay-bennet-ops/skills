# PointsYeah Hotel Search Skill

Search hotel award availability and pricing across loyalty programs via the PointsYeah API.

## Usage

```bash
node scripts/pointsyeah-hotel-api.js --location "Miami" --checkin 2026-08-15 --checkout 2026-08-18
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--location` | City, hotel, airport, or landmark (required) | - |
| `--checkin` | Check-in date YYYY-MM-DD (required) | - |
| `--checkout` | Check-out date YYYY-MM-DD (required) | - |
| `--adults` | Number of adults | 2 |
| `--children` | Number of children | 0 |
| `--rooms` | Number of rooms | 1 |
| `--lat` | Latitude (skip autocomplete) | - |
| `--lng` | Longitude (skip autocomplete) | - |
| `--json` | Output raw JSON | false |

### Output

Results sorted by CPP (cents per point) descending — best value first.

For each hotel:
- Name, program, distance from search location
- Points price per night (standard room)
- Cash price per night
- CPP value
- Alternative room types (suites, premium)
- OTA comparison prices (when available)

### Programs Supported

Hotels: Hyatt, Marriott, Choice, Wyndham, Hilton, IHG
OTA: Amex Travel, AAdvantage Hotels, United Hotels, Kayak, Virtuoso

Bank programs: Chase, Bilt, Amex, Capital One, Citi, Wells Fargo

## API Details

- **Search endpoint**: `POST https://api.pointsyeah.com/v2/live/hotel/search`
- **Offers endpoint**: `POST https://api.pointsyeah.com/v2/live/hotel/offers`
- **Auth**: Cognito refresh token → idToken
- **Encryption**: AES-256-CBC (same as flight search)

## Authentication

Uses the same Cognito refresh token as the flight search skill. Token is hardcoded in the script (same as `pointsyeah-api.js`). Set `PY_REFRESH_TOKEN` env var to override.

To get a fresh refresh token: log into pointsyeah.com, check cookies for `CognitoIdentityServiceProvider.*.refreshToken`.

## Notes

- IHG results may fail (different auth requirement)
- Search returns up to ~250 hotels within 30km radius
- Offers are fetched in parallel per program (~5-10 seconds total)
- Some hotels may show as "unavailable" if sold out or not bookable with points
