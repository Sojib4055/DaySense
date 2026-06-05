"""Rule-based human-impact scoring for DaySense AI."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from config import DAY_SCORE_LABELS
from data_parser import WeatherSnapshot, extract_hour, format_snapshot_time


@dataclass(frozen=True)
class DayScore:
    score: int
    label: str
    reasons: list[str]


@dataclass(frozen=True)
class ProductivityWindow:
    label: str
    score: int
    reason: str


@dataclass(frozen=True)
class OutdoorComfort:
    status: str
    safe_windows: list[str]
    risky_windows: list[str]
    reason: str


@dataclass(frozen=True)
class SleepComfort:
    status: str
    reason: str
    avg_temperature: float | None
    avg_humidity: float | None


@dataclass(frozen=True)
class MoodEnergyImpact:
    level: str
    note: str


@dataclass(frozen=True)
class HealthDiscomfort:
    level: str
    note: str


def calculate_day_score(
    temp: float | None,
    humidity: float | None,
    rain_prob: float | None,
    wind_speed: float | None,
    cloud_cover: float | None,
) -> DayScore:
    """Calculate the documented 0-100 DaySense day score."""

    score = 100
    reasons: list[str] = []

    if _gte(temp, 35):
        score -= 20
        reasons.append("very high temperature")
    elif _gte(temp, 30):
        score -= 10
        reasons.append("warm temperature")

    if _gte(humidity, 85):
        score -= 15
        reasons.append("very high humidity")
    elif _gte(humidity, 75):
        score -= 8
        reasons.append("high humidity")

    if _gte(rain_prob, 70):
        score -= 20
        reasons.append("high rain probability")
    elif _gte(rain_prob, 40):
        score -= 10
        reasons.append("moderate rain probability")

    if _gte(wind_speed, 35):
        score -= 10
        reasons.append("strong wind")
    elif _gte(wind_speed, 25):
        score -= 5
        reasons.append("breezy conditions")

    if _gte(cloud_cover, 85):
        score -= 5
        reasons.append("heavy cloud cover")

    score = max(int(score), 0)
    return DayScore(score=score, label=label_day_score(score), reasons=reasons)


def label_day_score(score: int) -> str:
    for threshold, label in DAY_SCORE_LABELS:
        if score >= threshold:
            return label
    return "Poor day"


def analyze_day(snapshot: WeatherSnapshot) -> DayScore:
    return calculate_day_score(
        snapshot.temperature,
        snapshot.humidity,
        snapshot.rain_probability,
        snapshot.wind_speed,
        snapshot.cloud_cover,
    )


def score_productivity_hour(hour: WeatherSnapshot) -> int:
    hour_score = 100
    if _gt(hour.temperature, 32):
        hour_score -= 20
    if _gt(hour.humidity, 80):
        hour_score -= 15
    if _gt(hour.rain_probability, 50):
        hour_score -= 20
    if _gt(hour.wind_speed, 30):
        hour_score -= 10
    return max(hour_score, 0)


def find_productivity_window(hourly: list[WeatherSnapshot]) -> ProductivityWindow:
    """Choose the best continuous 2-3 hour block for focus work."""

    if not hourly:
        return ProductivityWindow(
            label="Not enough hourly data",
            score=0,
            reason="Hourly forecast data is needed to select a focus window.",
        )

    window_size = 3 if len(hourly) >= 3 else 2 if len(hourly) >= 2 else 1
    best_start = 0
    best_score = -1.0

    for start in range(0, len(hourly) - window_size + 1):
        block = hourly[start : start + window_size]
        block_score = mean(score_productivity_hour(hour) for hour in block)
        if block_score > best_score:
            best_score = block_score
            best_start = start

    block = hourly[best_start : best_start + window_size]
    reasons = _productivity_reasons(block)
    label = _format_window(block)
    return ProductivityWindow(
        label=label,
        score=int(round(best_score)),
        reason=reasons or "This period has the best combined comfort score.",
    )


def evaluate_outdoor_hour(hour: WeatherSnapshot) -> str:
    if _gte(hour.temperature, 35) and _gte(hour.humidity, 80):
        return "Poor"
    if _gte(hour.rain_probability, 70):
        return "Risky"
    if _gte(hour.wind_speed, 35):
        return "Risky"
    return "Good"


def analyze_outdoor_comfort(hourly: list[WeatherSnapshot], fallback: WeatherSnapshot) -> OutdoorComfort:
    if not hourly:
        status = evaluate_outdoor_hour(fallback)
        return OutdoorComfort(
            status=status,
            safe_windows=["Current conditions"] if status == "Good" else [],
            risky_windows=["Current conditions"] if status != "Good" else [],
            reason=_outdoor_reason(fallback, status),
        )

    statuses = [(hour, evaluate_outdoor_hour(hour)) for hour in hourly]
    risky = [hour for hour, status in statuses if status != "Good"]
    safe = [hour for hour, status in statuses if status == "Good"]
    worst_status = "Poor" if any(status == "Poor" for _, status in statuses) else "Risky" if risky else "Good"

    focus_hour = risky[0] if risky else safe[0]
    return OutdoorComfort(
        status=worst_status,
        safe_windows=_group_windows(safe)[:3],
        risky_windows=_group_windows(risky)[:3],
        reason=_outdoor_reason(focus_hour, worst_status),
    )


def analyze_sleep_comfort(hourly: list[WeatherSnapshot], fallback: WeatherSnapshot) -> SleepComfort:
    night_hours = [
        hour
        for hour in hourly
        if (parsed_hour := extract_hour(hour.time)) is not None and (parsed_hour >= 21 or parsed_hour <= 6)
    ]
    source = night_hours or [fallback]

    temps = [hour.temperature for hour in source if hour.temperature is not None]
    humidities = [hour.humidity for hour in source if hour.humidity is not None]
    avg_temp = mean(temps) if temps else None
    avg_humidity = mean(humidities) if humidities else None

    if _gt(avg_temp, 28) and _gt(avg_humidity, 80):
        status = "Low"
        reason = "Night heat and humidity may make sleep less comfortable."
    elif _gt(avg_temp, 26) or _gt(avg_humidity, 75):
        status = "Medium"
        reason = "Night conditions may need cooling or ventilation."
    else:
        status = "Good"
        reason = "Night conditions look reasonably comfortable."

    return SleepComfort(
        status=status,
        reason=reason,
        avg_temperature=round(avg_temp, 1) if avg_temp is not None else None,
        avg_humidity=round(avg_humidity, 1) if avg_humidity is not None else None,
    )


def analyze_mood_energy(snapshot: WeatherSnapshot) -> MoodEnergyImpact:
    if _gt(snapshot.cloud_cover, 85) and _gt(snapshot.rain_probability, 50):
        return MoodEnergyImpact(
            level="Medium",
            note="Cloudy and rainy weather may make the day feel heavier.",
        )
    if _gt(snapshot.temperature, 35) and _gt(snapshot.humidity, 80):
        return MoodEnergyImpact(
            level="Medium",
            note="Heat and humidity may reduce comfort and daily energy.",
        )
    return MoodEnergyImpact(
        level="Low",
        note="Weather impact on comfort and energy appears limited.",
    )


def analyze_health_discomfort(snapshot: WeatherSnapshot) -> HealthDiscomfort:
    if _gte(snapshot.temperature, 35) and _gte(snapshot.humidity, 80):
        return HealthDiscomfort(
            level="High",
            note="Heat and humidity can feel physically uncomfortable; hydrate and limit peak outdoor exposure.",
        )
    if _gte(snapshot.rain_probability, 70) or _gte(snapshot.wind_speed, 35):
        return HealthDiscomfort(
            level="Medium",
            note="Rain or wind may increase travel and outdoor discomfort.",
        )
    if _gte(snapshot.humidity, 75) or _gte(snapshot.temperature, 30):
        return HealthDiscomfort(
            level="Medium",
            note="Warm or humid conditions may feel tiring during long outdoor periods.",
        )
    return HealthDiscomfort(
        level="Low",
        note="Weather-related discomfort risk looks low.",
    )


def _gt(value: float | None, threshold: float) -> bool:
    return value is not None and value > threshold


def _gte(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold


def _format_window(hours: list[WeatherSnapshot]) -> str:
    if not hours:
        return "N/A"
    if len(hours) == 1:
        return format_snapshot_time(hours[0])

    start_hour = extract_hour(hours[0].time)
    end_hour = extract_hour(hours[-1].time)
    if start_hour is not None and end_hour is not None:
        return f"{_hour_label(start_hour)} - {_hour_label((end_hour + 1) % 24)}"

    return f"{format_snapshot_time(hours[0])} - {format_snapshot_time(hours[-1])}"


def _hour_label(hour: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    return f"{hour % 12 or 12} {suffix}"


def _group_windows(hours: list[WeatherSnapshot]) -> list[str]:
    if not hours:
        return []

    groups: list[list[WeatherSnapshot]] = []
    current_group: list[WeatherSnapshot] = []
    previous_hour: int | None = None

    for snapshot in hours:
        parsed_hour = extract_hour(snapshot.time)
        if current_group and parsed_hour is not None and previous_hour is not None:
            expected = (previous_hour + 1) % 24
            if parsed_hour != expected:
                groups.append(current_group)
                current_group = []
        elif current_group and parsed_hour is None:
            groups.append(current_group)
            current_group = []

        current_group.append(snapshot)
        previous_hour = parsed_hour

    if current_group:
        groups.append(current_group)

    return [_format_window(group) for group in groups]


def _productivity_reasons(block: list[WeatherSnapshot]) -> str:
    avg_temp = _mean_or_none(hour.temperature for hour in block)
    avg_humidity = _mean_or_none(hour.humidity for hour in block)
    avg_rain = _mean_or_none(hour.rain_probability for hour in block)

    reasons: list[str] = []
    if avg_temp is not None and avg_temp <= 32:
        reasons.append("temperature is manageable")
    if avg_humidity is not None and avg_humidity <= 80:
        reasons.append("humidity is lower")
    if avg_rain is not None and avg_rain <= 50:
        reasons.append("rain chance is lower")

    if not reasons:
        return "This period has fewer weather penalties than the rest of the forecast."
    return ", ".join(reasons).capitalize() + "."


def _outdoor_reason(hour: WeatherSnapshot, status: str) -> str:
    if status == "Poor":
        return "Heat and humidity make long outdoor activity uncomfortable."
    if _gte(hour.rain_probability, 70):
        return "Rain probability is high during the risky period."
    if _gte(hour.wind_speed, 35):
        return "Wind speed may make outdoor activity risky."
    return "No major heat, rain, or wind risk is visible in the selected forecast."


def _mean_or_none(values: Iterable[float | None]) -> float | None:
    numbers = [value for value in values if value is not None]
    return mean(numbers) if numbers else None
