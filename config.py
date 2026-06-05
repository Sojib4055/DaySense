"""Configuration for the DaySense AI Streamlit app."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

WEATHER_AI_BASE_URL = os.getenv("WEATHER_AI_BASE_URL", "https://api.weather-ai.co")
WEATHER_AI_API_KEY = os.getenv("WEATHER_AI_API_KEY", "")
WEATHER_AI_USE_SYSTEM_PROXY = os.getenv("WEATHER_AI_USE_SYSTEM_PROXY", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

DEFAULT_UNITS = os.getenv("WEATHER_AI_UNITS", "metric")
DEFAULT_LANG = os.getenv("WEATHER_AI_LANG", "en")
DEFAULT_DAYS = 7
FREE_PLAN_MAX_DAYS = 7
REQUEST_TIMEOUT_SECONDS = 20

SUPPORTED_UNITS = ("metric", "imperial")
PURPOSE_OPTIONS = (
    "General day planning",
    "Work",
    "Study",
    "Travel",
    "Outdoor work",
    "Exercise",
    "Sleep planning",
)

DAY_SCORE_LABELS = (
    (85, "Excellent day"),
    (70, "Good day"),
    (50, "Moderate day"),
    (30, "Uncomfortable day"),
    (0, "Poor day"),
)
