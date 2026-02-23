"""Shared utilities for flight search scripts."""

import base64
import json
import os
import re
from copy import deepcopy

from fli.models import FlightSearchFilters
from fli.models.google_flights.base import TripType
from fli.search import SearchFlights
from fli.search.client import get_client

BASE_URL = "https://www.google.com/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/GetShoppingResults"

# Load preferences from data/preferences.json
PREFS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "preferences.json")

def _load_prefs():
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE) as f:
            return json.load(f)
    return {}

PREFS = _load_prefs()
DEFAULT_EXCLUDE = set(PREFS.get("exclude_airlines", []))


def _extract_currency(token_b64):
    try:
        decoded = base64.b64decode(token_b64)
        match = re.search(rb"\x1a\x03([A-Z]{3})", decoded)
        if match:
            return match.group(1).decode("ascii")
    except Exception:
        pass
    return None


def _raw_search(filters):
    client = get_client()
    encoded = filters.encode()
    response = client.post(
        url=BASE_URL,
        data=f"f.req={encoded}",
        impersonate="chrome",
        allow_redirects=True,
    )
    response.raise_for_status()
    parsed = json.loads(response.text.lstrip(")]}'"))[0][2]
    if not parsed:
        return None
    return json.loads(parsed)


def search_with_currency(filters: FlightSearchFilters, top_n: int = 10):
    data = _raw_search(filters)
    if data is None:
        return None, "USD"

    currency = None
    flights_data = []
    for i in [2, 3]:
        if i < len(data) and isinstance(data[i], list):
            for item in data[i][0]:
                flights_data.append(item)
                if currency is None and len(item[1]) > 1 and isinstance(item[1][1], str):
                    currency = _extract_currency(item[1][1])

    results = [SearchFlights._parse_flights_data(flight) for flight in flights_data]

    if filters.trip_type == TripType.ONE_WAY or filters.flight_segments[0].selected_flight is not None:
        return results, currency or "USD"

    # Round-trip: get return flights for top outbound options
    flight_pairs = []
    searcher = SearchFlights()
    for selected_flight in results[:top_n]:
        selected_filters = deepcopy(filters)
        selected_filters.flight_segments[0].selected_flight = selected_flight
        return_flights = searcher.search(selected_filters, top_n=top_n)
        if return_flights is not None:
            flight_pairs.extend(
                (selected_flight, ret) for ret in return_flights
            )

    return flight_pairs, currency or "USD"


def filter_results(results, exclude_airlines=None, include_airlines=None,
                   depart_after=None, depart_before=None, max_duration=None,
                   max_stops=None, is_round_trip=False):
    """Post-filter results by airline, time, duration, stops."""
    if exclude_airlines is None:
        exclude_airlines = DEFAULT_EXCLUDE

    filtered = []
    for result in results:
        if is_round_trip and isinstance(result, tuple):
            outbound, ret = result
            flights_to_check = [outbound, ret]
        else:
            flights_to_check = [result]

        skip = False
        for flight in flights_to_check:
            # Airline filter
            flight_airlines = {leg.airline.code for leg in flight.legs if hasattr(leg.airline, 'code')}
            if not flight_airlines:
                flight_airlines = {leg.airline.name for leg in flight.legs}

            if exclude_airlines:
                if flight_airlines & exclude_airlines:
                    skip = True
                    break

            if include_airlines:
                if not (flight_airlines & include_airlines):
                    skip = True
                    break

            # Stop filter
            if max_stops is not None and flight.stops > max_stops:
                skip = True
                break

            # Duration filter (minutes)
            if max_duration and flight.duration > max_duration:
                skip = True
                break

            # Time filter (hour of day, on first leg departure)
            if flight.legs:
                dep_hour = flight.legs[0].departure_datetime.hour
                if depart_after is not None and dep_hour < depart_after:
                    skip = True
                    break
                if depart_before is not None and dep_hour >= depart_before:
                    skip = True
                    break

        if not skip:
            filtered.append(result)

    return filtered


def format_flight(flight, currency="USD"):
    """Format a single flight into a dict."""
    legs = []
    for leg in flight.legs:
        legs.append({
            "airline": leg.airline.name,
            "airline_code": getattr(leg.airline, 'code', ''),
            "flight_number": leg.flight_number,
            "departure_airport": leg.departure_airport.name,
            "departure_time": leg.departure_datetime.strftime("%I:%M %p"),
            "departure_date": leg.departure_datetime.strftime("%Y-%m-%d"),
            "arrival_airport": leg.arrival_airport.name,
            "arrival_time": leg.arrival_datetime.strftime("%I:%M %p"),
            "arrival_date": leg.arrival_datetime.strftime("%Y-%m-%d"),
        })

    h, m = divmod(flight.duration, 60)
    return {
        "price": flight.price,
        "currency": currency,
        "duration": f"{h}h {m}m",
        "duration_min": flight.duration,
        "stops": flight.stops,
        "legs": legs,
    }


def format_results(results, currency="USD", is_round_trip=False):
    """Format all results into JSON-serializable list."""
    formatted = []
    for result in results:
        if is_round_trip and isinstance(result, tuple):
            outbound, ret = result
            formatted.append({
                "total_price": outbound.price + ret.price,
                "currency": currency,
                "outbound": format_flight(outbound, currency),
                "return": format_flight(ret, currency),
            })
        else:
            formatted.append(format_flight(result, currency))
    return formatted


def format_text(results, currency="USD", is_round_trip=False):
    """Format results as human-readable text."""
    lines = []
    for i, result in enumerate(results, 1):
        if is_round_trip and isinstance(result, tuple):
            outbound, ret = result
            total = outbound.price + ret.price
            h1, m1 = divmod(outbound.duration, 60)
            h2, m2 = divmod(ret.duration, 60)
            lines.append(f"\nOption {i}: ${total:.0f} total")
            lines.append(f"  OUT: ${outbound.price:.0f} | {h1}h{m1}m | {outbound.stops} stop(s)")
            for leg in outbound.legs:
                lines.append(f"    {leg.airline.name} {leg.flight_number}: {leg.departure_airport.name} {leg.departure_datetime.strftime('%I:%M %p')} → {leg.arrival_airport.name} {leg.arrival_datetime.strftime('%I:%M %p')}")
            lines.append(f"  RET: ${ret.price:.0f} | {h2}h{m2}m | {ret.stops} stop(s)")
            for leg in ret.legs:
                lines.append(f"    {leg.airline.name} {leg.flight_number}: {leg.departure_airport.name} {leg.departure_datetime.strftime('%I:%M %p')} → {leg.arrival_airport.name} {leg.arrival_datetime.strftime('%I:%M %p')}")
        else:
            flight = result
            h, m = divmod(flight.duration, 60)
            lines.append(f"\nOption {i}: ${flight.price:.0f} | {h}h{m}m | {flight.stops} stop(s)")
            for leg in flight.legs:
                lines.append(f"  {leg.airline.name} {leg.flight_number}: {leg.departure_airport.name} {leg.departure_datetime.strftime('%I:%M %p')} → {leg.arrival_airport.name} {leg.arrival_datetime.strftime('%I:%M %p')}")
    return "\n".join(lines)
