"""Normalize WeatherAI JSON into values used by the DaySense engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


@dataclass(frozen=True)
class WeatherSnapshot:
    """Weather values for one current, daily, or hourly record."""

    time: str = ""
    date: str = ""
    temperature: float | None = None
    humidity: float | None = None
    rain_probability: float | None = None
    wind_speed: float | None = None
    cloud_cover: float | None = None
    condition: str = "Unknown"
    raw: dict[str, Any] = field(default_factory=dict)

    def has_core_values(self) -> bool:
        return any(
            value is not None
            for value in (
                self.temperature,
                self.humidity,
                self.rain_probability,
                self.wind_speed,
                self.cloud_cover,
            )
        )


@dataclass(frozen=True)
class ParsedWeather:
    """Parsed WeatherAI response used by the UI and scoring layer."""

    current: WeatherSnapshot
    daily: list[WeatherSnapshot]
    hourly: list[WeatherSnapshot]
    location_name: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


CURRENT_KEYS = ("current", "current_weather", "now", "conditions")
DAILY_KEYS = ("daily", "days", "forecast_days", "daily_forecast")
HOURLY_KEYS = ("hourly", "hours", "hourly_forecast")
FORECAST_KEYS = ("forecast", "forecast_data", "weather", "data")

TEMP_KEYS = (
    "temperature",
    "temp",
    "temp_c",
    "temperature_c",
    "temperature_2m",
    "feels_like",
)
DAILY_TEMP_KEYS = (
    "max_temp",
    "temp_max",
    "temperature_max",
    "high",
    "high_temp",
    "avg_temp",
    "temperature_avg",
    "temperature",
    "temp",
)
HUMIDITY_KEYS = (
    "humidity",
    "relative_humidity",
    "relativeHumidity",
    "humidity_percent",
    "relative_humidity_2m",
    "avg_humidity",
)
RAIN_KEYS = (
    "rain_probability",
    "rain_prob",
    "rain_chance",
    "chance_of_rain",
    "precipitation_probability",
    "precip_probability",
    "precip_prob",
    "pop",
)
WIND_KEYS = (
    "wind_speed",
    "windSpeed",
    "windspeed",
    "wind_kph",
    "windSpeedKph",
    "wind_speed_10m",
    "max_wind_speed",
)
CLOUD_KEYS = (
    "cloud_cover",
    "cloudCover",
    "clouds",
    "cloudiness",
    "cloud_cover_percentage",
)
CONDITION_KEYS = ("condition", "weather", "summary", "description", "text", "icon_text")
TIME_KEYS = ("time", "datetime", "date_time", "dateTime", "timestamp", "valid_time", "hour")
DATE_KEYS = ("date", "day", "forecast_date")


def parse_weather_payload(payload: dict[str, Any]) -> ParsedWeather:
    """Extract current, daily, and hourly values from a WeatherAI response."""

    root = _unwrap_payload(payload)
    current_section = _find_section(root, CURRENT_KEYS)
    daily_section = _find_section(root, DAILY_KEYS)
    hourly_section = _find_section(root, HOURLY_KEYS)

    current = normalize_snapshot(current_section or root)
    daily = [
        normalize_snapshot(item, prefer_daily=True)
        for item in _coerce_records(daily_section, DAILY_KEYS)
    ]
    hourly = [normalize_snapshot(item) for item in _coerce_records(hourly_section, HOURLY_KEYS)]

    if not current.has_core_values() and hourly:
        current = hourly[0]
    if not daily:
        daily = [normalize_snapshot(current.raw, prefer_daily=True)] if current.raw else [current]

    return ParsedWeather(
        current=current,
        daily=daily,
        hourly=hourly,
        location_name=_extract_location(root),
        raw=payload,
    )


def normalize_snapshot(data: Any, *, prefer_daily: bool = False) -> WeatherSnapshot:
    """Turn one API record into a consistent WeatherSnapshot."""

    if not isinstance(data, dict):
        return WeatherSnapshot()

    flat = _flatten_weather_record(data)
    condition = _first_text(flat, CONDITION_KEYS) or "Unknown"

    return WeatherSnapshot(
        time=_first_text(flat, TIME_KEYS) or "",
        date=_first_text(flat, DATE_KEYS) or "",
        temperature=_first_number(flat, DAILY_TEMP_KEYS if prefer_daily else TEMP_KEYS),
        humidity=_first_number(flat, HUMIDITY_KEYS),
        rain_probability=_normalize_percentage(_first_number(flat, RAIN_KEYS)),
        wind_speed=_first_number(flat, WIND_KEYS),
        cloud_cover=_normalize_percentage(_first_number(flat, CLOUD_KEYS)),
        condition=condition,
        raw=data,
    )


def extract_hour(value: str) -> int | None:
    """Best-effort hour extraction for ISO timestamps and simple hour labels."""

    if not value:
        return None

    text = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).hour
        except ValueError:
            pass

    if "T" in text:
        text = text.split("T", 1)[1]
    if " " in text:
        text = text.rsplit(" ", 1)[-1]
    if ":" in text:
        text = text.split(":", 1)[0]

    try:
        hour = int("".join(ch for ch in text if ch.isdigit())[:2])
    except ValueError:
        return None

    if 0 <= hour <= 23:
        return hour
    return None


def format_snapshot_time(snapshot: WeatherSnapshot) -> str:
    """Return a compact display label for a snapshot time."""

    if snapshot.time:
        hour = extract_hour(snapshot.time)
        if hour is not None:
            suffix = "AM" if hour < 12 else "PM"
            hour_12 = hour % 12 or 12
            return f"{hour_12} {suffix}"
        return snapshot.time
    if snapshot.date:
        return snapshot.date
    return "N/A"


def _unwrap_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("data", "result", "weather"):
        value = payload.get(key)
        if isinstance(value, dict) and any(section in value for section in CURRENT_KEYS + DAILY_KEYS + HOURLY_KEYS):
            return value
    return payload


def _find_section(data: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value

    for parent_key in FORECAST_KEYS:
        parent = data.get(parent_key)
        if isinstance(parent, dict):
            for key in keys:
                value = parent.get(key)
                if value is not None:
                    return value
    return None


def _coerce_records(section: Any, known_keys: Iterable[str]) -> list[dict[str, Any]]:
    if isinstance(section, list):
        return [item for item in section if isinstance(item, dict)]

    if isinstance(section, dict):
        for key in tuple(known_keys) + ("data", "items", "forecast"):
            value = section.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if any(key in section for key in TEMP_KEYS + DAILY_TEMP_KEYS + HUMIDITY_KEYS):
            return [section]

    return []


def _flatten_weather_record(data: dict[str, Any]) -> dict[str, Any]:
    flat = dict(data)
    for key in ("values", "details", "weather", "condition", "main"):
        nested = data.get(key)
        if isinstance(nested, dict):
            flat.update({nested_key: nested_value for nested_key, nested_value in nested.items()})
    return flat


def _first_number(data: dict[str, Any], keys: Iterable[str]) -> float | None:
    for key in keys:
        value = data.get(key)
        number = _to_float(value)
        if number is not None:
            return number
    return None


def _first_text(data: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            text = _first_text(value, ("text", "description", "summary", "main", "name"))
            if text:
                return text
    return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "").replace("C", "").replace("F", "")
        cleaned = cleaned.replace("km/h", "").replace("mph", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _normalize_percentage(value: float | None) -> float | None:
    if value is None:
        return None
    if 0 <= value <= 1:
        return value * 100
    return value


def _extract_location(data: dict[str, Any]) -> str:
    location = data.get("location") or data.get("place")
    if isinstance(location, str):
        return location
    if isinstance(location, dict):
        parts = [
            location.get("name"),
            location.get("city"),
            location.get("region"),
            location.get("country"),
        ]
        unique_parts = []
        for part in parts:
            if isinstance(part, str) and part and part not in unique_parts:
                unique_parts.append(part)
        return ", ".join(unique_parts)
    return ""

