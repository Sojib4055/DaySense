"""WeatherAI API client and error handling."""

from __future__ import annotations

from typing import Any

import requests

import config


ERROR_MESSAGES = {
    400: "Please enter valid latitude and longitude.",
    401: "Invalid or missing WeatherAI API key.",
    403: "This feature is not available in your current WeatherAI plan.",
    429: "API quota exceeded. Please check WeatherAI usage.",
    500: "WeatherAI server error. Please try again later.",
    503: "Weather service is temporarily unavailable.",
}


class WeatherAIError(RuntimeError):
    """Raised when WeatherAI cannot return usable weather data."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class WeatherAIClient:
    """Small client for WeatherAI v1 endpoints."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        timeout: int | None = None,
        use_system_proxy: bool | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = (base_url or config.WEATHER_AI_BASE_URL).rstrip("/")
        self.timeout = timeout or config.REQUEST_TIMEOUT_SECONDS
        if use_system_proxy is None:
            use_system_proxy = bool(getattr(config, "WEATHER_AI_USE_SYSTEM_PROXY", False))
        self.use_system_proxy = use_system_proxy
        self.session = requests.Session()
        self.session.trust_env = use_system_proxy

    def get_weather(
        self,
        *,
        lat: float,
        lon: float,
        days: int = 7,
        units: str = "metric",
        ai: bool = False,
        lang: str = "en",
    ) -> dict[str, Any]:
        """Fetch current conditions plus forecast from GET /v1/weather."""

        params: dict[str, Any] = {
            "lat": lat,
            "lon": lon,
            "days": days,
            "units": units,
            "ai": str(ai).lower(),
            "lang": lang,
        }
        return self._get("/v1/weather", params=params)

    def get_current(self, *, lat: float, lon: float, units: str = "metric") -> dict[str, Any]:
        """Fetch current conditions from GET /v1/current."""

        return self._get("/v1/current", params={"lat": lat, "lon": lon, "units": units})

    def get_daily(
        self,
        *,
        lat: float,
        lon: float,
        days: int = 7,
        units: str = "metric",
    ) -> dict[str, Any]:
        """Fetch daily forecast data from GET /v1/daily."""

        return self._get(
            "/v1/daily",
            params={"lat": lat, "lon": lon, "days": days, "units": units},
        )

    def get_hourly(
        self,
        *,
        lat: float,
        lon: float,
        days: int = 2,
        units: str = "metric",
    ) -> dict[str, Any]:
        """Fetch hourly forecast data from GET /v1/hourly."""

        return self._get(
            "/v1/hourly",
            params={"lat": lat, "lon": lon, "days": days, "units": units},
        )

    def get_usage(self) -> dict[str, Any]:
        """Fetch optional quota details from GET /v1/usage."""

        return self._get("/v1/usage")

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise WeatherAIError(ERROR_MESSAGES[401], status_code=401)

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _get(self, endpoint: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(
                url,
                headers=self._headers(),
                params=params,
                proxies=self._proxy_settings(),
                timeout=self.timeout,
            )
        except requests.exceptions.ProxyError as exc:
            raise WeatherAIError(
                "Could not connect to WeatherAI because the system proxy setting is not reachable. "
                "This app ignores system proxies by default; restart Streamlit and try again. "
                "If you intentionally need a proxy, set WEATHER_AI_USE_SYSTEM_PROXY=true.",
            ) from exc
        except requests.RequestException as exc:
            raise WeatherAIError(f"Could not connect to WeatherAI: {exc}") from exc

        if response.status_code >= 400:
            message = ERROR_MESSAGES.get(
                response.status_code,
                f"WeatherAI request failed with status {response.status_code}.",
            )
            raise WeatherAIError(
                message,
                status_code=response.status_code,
                response_text=response.text,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise WeatherAIError("WeatherAI returned a non-JSON response.") from exc

        if not isinstance(payload, dict):
            raise WeatherAIError("WeatherAI returned an unexpected response shape.")

        return payload

    def _proxy_settings(self) -> dict[str, str] | None:
        if self.use_system_proxy:
            return None
        return {
            "http": "",
            "https": "",
            "all": "",
        }
