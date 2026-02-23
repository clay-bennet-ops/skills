# Travel Skills — Claude Code Plugin Marketplace

A plugin marketplace for Claude Code with award travel and flight search tools.

## Plugins

| Plugin | Description |
|--------|-------------|
| **pointsyeah-flights** | Search award flights bookable with points/miles via PointsYeah |
| **pointsyeah-hotels** | Search hotel award availability and pricing via PointsYeah |
| **google-flights** | Search cash flight prices via Google Flights with price tracking |

## Install

Add the marketplace and install plugins:

```bash
/plugin marketplace add https://github.com/clay-bennet-ops/skills
/plugin install pointsyeah-flights@travel-skills
/plugin install pointsyeah-hotels@travel-skills
/plugin install google-flights@travel-skills
```

## Plugin Details

### pointsyeah-flights
Search award flights across all major loyalty programs. Supports Chase UR, Bilt, Amex MR, Capital One, Citi, and Wells Fargo transfer partners.

**Requires**: Node.js, PointsYeah account (free), Cognito refresh token

### pointsyeah-hotels
Search hotel award availability and pricing. Compare points prices across Hyatt, Marriott, Hilton, IHG, Choice, and Wyndham with OTA price comparisons.

**Requires**: Node.js, PointsYeah account (free), Cognito refresh token

### google-flights
Search cash flight prices with multi-airport support, round-trip/one-way, separate ticket pricing, airline filtering, and price tracking with alerts.

**Requires**: Python 3, `flights` library (`pip install flights`)

## License

MIT
