"""Convert DaySense analysis results into readable advice."""

from __future__ import annotations

from impact_engine import (
    DayScore,
    HealthDiscomfort,
    MoodEnergyImpact,
    OutdoorComfort,
    ProductivityWindow,
    SleepComfort,
)


def build_final_recommendation(
    *,
    purpose: str,
    day_score: DayScore,
    productivity: ProductivityWindow,
    outdoor: OutdoorComfort,
    sleep: SleepComfort,
    mood: MoodEnergyImpact,
    health: HealthDiscomfort,
) -> str:
    """Create one practical daily plan from the computed impact signals."""

    purpose = purpose.lower()
    advice: list[str] = []

    if productivity.score > 0:
        advice.append(f"Plan important focus work around {productivity.label}")

    if outdoor.status in {"Poor", "Risky"}:
        risky_window = outdoor.risky_windows[0] if outdoor.risky_windows else "the risky forecast window"
        advice.append(f"reduce outdoor exposure around {risky_window}")
    elif outdoor.safe_windows:
        advice.append(f"use {outdoor.safe_windows[0]} for outdoor plans")

    if sleep.status != "Good":
        advice.append("keep the room cool and ventilated tonight")

    if health.level in {"Medium", "High"}:
        advice.append("keep water nearby")

    if "travel" in purpose and outdoor.status != "Good":
        advice.append("allow extra travel time")
    elif "exercise" in purpose and outdoor.status != "Good":
        advice.append("prefer indoor or lighter exercise")
    elif "sleep" in purpose and sleep.status != "Good":
        advice.append("prepare for warmer or more humid night conditions")

    if day_score.score >= 85 and mood.level == "Low":
        return "Weather conditions look supportive today; keep your main plans but still check updates before leaving."

    if not advice:
        return "Keep a normal schedule today and check the forecast again before outdoor plans."

    return _sentence_join(advice) + "."


def day_score_summary(day_score: DayScore) -> str:
    if not day_score.reasons:
        return "No major weather comfort penalties were detected."
    return "Main pressure points: " + ", ".join(day_score.reasons) + "."


def outdoor_summary(outdoor: OutdoorComfort) -> str:
    if outdoor.status == "Good":
        if outdoor.safe_windows:
            return f"Best visible outdoor window: {outdoor.safe_windows[0]}."
        return "Outdoor conditions look generally usable."

    risky = ", ".join(outdoor.risky_windows) if outdoor.risky_windows else "some forecast hours"
    return f"Use caution around {risky}. {outdoor.reason}"


def _sentence_join(parts: list[str]) -> str:
    if len(parts) == 1:
        return _capitalize_first(parts[0])
    return _capitalize_first(parts[0]) + ", " + ", ".join(parts[1:-1]) + ", and " + parts[-1]


def _capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:]
