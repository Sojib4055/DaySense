"""Resolve display locations for report headers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


COUNTRY_ONLY_LABELS = {
    "bd",
    "bangladesh",
    "ca",
    "canada",
    "gb",
    "uk",
    "united kingdom",
    "us",
    "usa",
    "united states",
    "united states of america",
}


@dataclass(frozen=True)
class DisplayLocation:
    title: str
    subtitle: str


def build_display_location(
    *,
    lat: float,
    lon: float,
    api_location: str,
    use_system_proxy: bool = False,
) -> DisplayLocation:
    """Return a useful location title plus exact coordinate subtitle."""

    cleaned_api_location = api_location.strip()
    if _is_specific_location(cleaned_api_location):
        return DisplayLocation(
            title=cleaned_api_location,
            subtitle=_coordinate_label(lat, lon),
        )

    reverse_location = _reverse_geocode(lat, lon, use_system_proxy=use_system_proxy)
    if reverse_location:
        return DisplayLocation(
            title=reverse_location,
            subtitle=_coordinate_label(lat, lon),
        )

    if cleaned_api_location:
        return DisplayLocation(
            title=f"{cleaned_api_location} ({lat:.4f}, {lon:.4f})",
            subtitle="WeatherAI returned only a broad location label.",
        )

    return DisplayLocation(
        title=_coordinate_label(lat, lon),
        subtitle="Exact coordinates",
    )


def _reverse_geocode(lat: float, lon: float, *, use_system_proxy: bool) -> str:
    session = requests.Session()
    session.trust_env = use_system_proxy

    try:
        response = session.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "format": "jsonv2",
                "lat": lat,
                "lon": lon,
                "zoom": 10,
                "addressdetails": 1,
            },
            headers={
                "User-Agent": "DaySenseAI/1.0 local Streamlit weather app",
                "Accept": "application/json",
            },
            proxies=None if use_system_proxy else {"http": "", "https": "", "all": ""},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return ""
    except ValueError:
        return ""

    if not isinstance(payload, dict):
        return ""

    address = payload.get("address")
    if not isinstance(address, dict):
        display_name = payload.get("display_name")
        return str(display_name).strip() if display_name else ""

    return _format_address(address)


def _format_address(address: dict[str, Any]) -> str:
    place = _first_text(
        address,
        (
            "city",
            "town",
            "village",
            "municipality",
            "suburb",
            "county",
        ),
    )
    state = _first_text(address, ("state", "region", "state_district"))
    country = _first_text(address, ("country",))

    parts: list[str] = []
    for part in (place, state, country):
        if part and part not in parts:
            parts.append(part)

    return ", ".join(parts)


def _first_text(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _is_specific_location(location: str) -> bool:
    if not location:
        return False
    normalized = location.strip().lower()
    if normalized in COUNTRY_ONLY_LABELS:
        return False
    return "," in location or len(location.split()) > 1


def _coordinate_label(lat: float, lon: float) -> str:
    return f"{lat:.6f}, {lon:.6f}"
