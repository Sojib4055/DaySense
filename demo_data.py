"""Sample WeatherAI-like payload for local UI testing without an API key."""

from __future__ import annotations


DEMO_WEATHER_PAYLOAD = {
    "location": {
        "city": "Dhaka",
        "country": "Bangladesh",
    },
    "current": {
        "temperature": 31,
        "humidity": 78,
        "rain_probability": 45,
        "wind_speed": 18,
        "cloud_cover": 72,
        "condition": {"text": "Cloudy"},
    },
    "forecast": {
        "daily": [
            {
                "date": "2026-06-05",
                "max_temp": 34,
                "humidity": 82,
                "rain_probability": 65,
                "wind_speed": 22,
                "cloud_cover": 88,
                "condition": "Humid and cloudy",
            }
        ],
        "hourly": [
            {
                "time": "2026-06-05T06:00:00",
                "temperature": 28,
                "humidity": 76,
                "rain_probability": 18,
                "wind_speed": 10,
                "cloud_cover": 50,
            },
            {
                "time": "2026-06-05T07:00:00",
                "temperature": 29,
                "humidity": 74,
                "rain_probability": 18,
                "wind_speed": 10,
                "cloud_cover": 46,
            },
            {
                "time": "2026-06-05T08:00:00",
                "temperature": 29,
                "humidity": 72,
                "rain_probability": 20,
                "wind_speed": 12,
                "cloud_cover": 45,
            },
            {
                "time": "2026-06-05T09:00:00",
                "temperature": 30,
                "humidity": 73,
                "rain_probability": 25,
                "wind_speed": 10,
                "cloud_cover": 50,
            },
            {
                "time": "2026-06-05T10:00:00",
                "temperature": 31,
                "humidity": 74,
                "rain_probability": 30,
                "wind_speed": 12,
                "cloud_cover": 60,
            },
            {
                "time": "2026-06-05T11:00:00",
                "temperature": 33,
                "humidity": 78,
                "rain_probability": 42,
                "wind_speed": 15,
                "cloud_cover": 70,
            },
            {
                "time": "2026-06-05T12:00:00",
                "temperature": 35,
                "humidity": 81,
                "rain_probability": 55,
                "wind_speed": 18,
                "cloud_cover": 84,
            },
            {
                "time": "2026-06-05T13:00:00",
                "temperature": 36,
                "humidity": 83,
                "rain_probability": 68,
                "wind_speed": 20,
                "cloud_cover": 88,
            },
            {
                "time": "2026-06-05T14:00:00",
                "temperature": 36,
                "humidity": 84,
                "rain_probability": 72,
                "wind_speed": 20,
                "cloud_cover": 90,
            },
            {
                "time": "2026-06-05T15:00:00",
                "temperature": 35,
                "humidity": 82,
                "rain_probability": 70,
                "wind_speed": 24,
                "cloud_cover": 92,
            },
            {
                "time": "2026-06-05T18:00:00",
                "temperature": 32,
                "humidity": 80,
                "rain_probability": 52,
                "wind_speed": 18,
                "cloud_cover": 86,
            },
            {
                "time": "2026-06-05T21:00:00",
                "temperature": 30,
                "humidity": 82,
                "rain_probability": 45,
                "wind_speed": 12,
                "cloud_cover": 80,
            },
            {
                "time": "2026-06-05T22:00:00",
                "temperature": 29,
                "humidity": 83,
                "rain_probability": 40,
                "wind_speed": 10,
                "cloud_cover": 80,
            },
        ],
    },
}
