# Travel Skills — Claude Code Plugin Marketplace

A plugin marketplace for Claude Code with award travel and flight search tools.

## Plugins

| Plugin | Description |
|--------|-------------|
| **pointsyeah-flights** | Search award flights bookable with points/miles via PointsYeah |
| **pointsyeah-hotels** | Search hotel award availability and pricing via PointsYeah |
| **google-flights** | Search cash flight prices via Google Flights with price tracking |
| **google-hotels** | Search hotel prices via Google Hotels with live date-accurate pricing |

## Install

Add the marketplace and install plugins:

```bash
/plugin marketplace add https://github.com/clay-bennet-ops/skills
/plugin install PointsYeah-flights@travel-skills
/plugin install PointsYeah-hotels@travel-skills
/plugin install Google-flights@travel-skills
/plugin install Google-hotels@travel-skills
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

### google-hotels
Search hotel prices with live, date-accurate pricing. Reverse-engineers Google Hotels' protobuf format to get real rates (not cached estimates). Supports any location, price/rating filters, deal detection, and price tracking.

**Requires**: Python 3, `curl-cffi` (`pip install curl-cffi`)

## License

MIT
