"""Streamlit interface for DaySense AI."""

from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
from html import escape
from pathlib import Path
from typing import Any


APP_PATH = Path(__file__).resolve()


def _streamlit_command() -> list[str]:
    scripts_dir = "Scripts" if sys.platform.startswith("win") else "bin"
    executable = "streamlit.exe" if sys.platform.startswith("win") else "streamlit"
    project_streamlit = APP_PATH.parent / ".venv" / scripts_dir / executable

    if project_streamlit.exists():
        return [str(project_streamlit)]
    if importlib.util.find_spec("streamlit") is not None:
        return [sys.executable, "-m", "streamlit"]
    return []


def _launch_with_streamlit() -> None:
    command = _streamlit_command()
    if not command:
        raise SystemExit(
            "Streamlit is not installed for this Python interpreter. "
            "Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        )

    raise SystemExit(subprocess.run(command + ["run", str(APP_PATH)], check=False).returncode)


if __name__ == "__main__" and importlib.util.find_spec("streamlit") is None:
    _launch_with_streamlit()

import streamlit as st

from config import (
    DEFAULT_DAYS,
    DEFAULT_LANG,
    DEFAULT_UNITS,
    FREE_PLAN_MAX_DAYS,
    PURPOSE_OPTIONS,
    SUPPORTED_UNITS,
    WEATHER_AI_API_KEY,
)
from data_parser import WeatherSnapshot, format_snapshot_time, parse_weather_payload
from demo_data import DEMO_WEATHER_PAYLOAD
from impact_engine import (
    analyze_day,
    analyze_health_discomfort,
    analyze_mood_energy,
    analyze_outdoor_comfort,
    analyze_sleep_comfort,
    evaluate_outdoor_hour,
    find_productivity_window,
    score_productivity_hour,
)
from location_resolver import build_display_location
from recommendation_engine import (
    build_final_recommendation,
    day_score_summary,
    outdoor_summary,
)
from weather_api import WeatherAIClient, WeatherAIError


def main() -> None:
    st.set_page_config(
        page_title="DaySense AI",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()

    st.markdown(
        """
        <section class="app-header">
            <div>
                <p class="eyebrow">Weather-Based Human Impact Intelligence</p>
                <h1>DaySense AI</h1>
            </div>
            <div class="header-chip">WeatherAI API v1</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    inputs = _render_inputs()

    if inputs["submitted"]:
        _render_report(inputs)
    else:
        _render_empty_state()


def _render_inputs() -> dict[str, Any]:
    with st.sidebar:
        st.header("Input Panel")
        lat = st.number_input("Latitude", value=23.8103, format="%.6f")
        lon = st.number_input("Longitude", value=90.4125, format="%.6f")
        days = st.slider("Forecast days", min_value=1, max_value=FREE_PLAN_MAX_DAYS, value=DEFAULT_DAYS)
        units = st.selectbox(
            "Display units",
            options=SUPPORTED_UNITS,
            index=SUPPORTED_UNITS.index(DEFAULT_UNITS) if DEFAULT_UNITS in SUPPORTED_UNITS else 0,
        )
        purpose = st.selectbox("Purpose", options=PURPOSE_OPTIONS)

        api_key = _resolve_api_key()
        api_key_source = _api_key_source(api_key)
        if api_key:
            st.caption(f"API key loaded from {api_key_source}.")
        else:
            api_key = st.text_input("WeatherAI API key", type="password", placeholder="wai_...")

        network_mode = "system proxy" if _use_system_proxy() else "direct connection"
        st.caption(f"WeatherAI network: {network_mode}.")

        use_demo = st.toggle("Demo forecast", value=not bool(api_key))
        show_raw = st.checkbox("Show raw API response", value=False)
        submitted = st.button("Generate report", type="primary", use_container_width=True)

    return {
        "lat": lat,
        "lon": lon,
        "days": days,
        "units": units,
        "purpose": purpose,
        "api_key": api_key,
        "use_demo": use_demo,
        "show_raw": show_raw,
        "submitted": submitted,
    }


def _render_report(inputs: dict[str, Any]) -> None:
    if not inputs["use_demo"] and not inputs["api_key"]:
        st.error("Live forecast needs a WeatherAI API key. Add it to .env or paste it in the sidebar.")
        st.info("For local testing without an API key, turn Demo forecast ON.")
        st.stop()

    try:
        payload = _fetch_weather(inputs)
        parsed = parse_weather_payload(payload)
    except WeatherAIError as exc:
        st.error(str(exc))
        if exc.response_text:
            with st.expander("WeatherAI response"):
                st.code(exc.response_text)
        st.stop()

    day_source = parsed.daily[0] if parsed.daily else parsed.current
    day_score = analyze_day(day_source)
    productivity = find_productivity_window(parsed.hourly)
    outdoor = analyze_outdoor_comfort(parsed.hourly, parsed.current)
    sleep = analyze_sleep_comfort(parsed.hourly, parsed.current)
    mood = analyze_mood_energy(day_source)
    health = analyze_health_discomfort(day_source)
    final_recommendation = build_final_recommendation(
        purpose=inputs["purpose"],
        day_score=day_score,
        productivity=productivity,
        outdoor=outdoor,
        sleep=sleep,
        mood=mood,
        health=health,
    )

    location = build_display_location(
        lat=inputs["lat"],
        lon=inputs["lon"],
        api_location=parsed.location_name,
        use_system_proxy=_use_system_proxy(),
    )
    _render_report_header(
        location.title,
        location.subtitle,
        day_score,
        productivity,
        outdoor,
        sleep,
        inputs["use_demo"],
    )

    tabs = st.tabs(["Dashboard", "Hourly Windows", "Methodology", "Raw Data"])

    with tabs[0]:
        _render_current_weather(parsed.current, inputs["units"])
        _render_score_cards(day_score, productivity, outdoor, sleep, mood, health)

        st.markdown("### Final Recommendation")
        st.markdown(
            f'<div class="recommendation">{escape(final_recommendation)}</div>',
            unsafe_allow_html=True,
        )

    with tabs[1]:
        _render_windows(productivity, outdoor, sleep, inputs["units"])
        _render_hourly_table(parsed.hourly, inputs["units"])

    with tabs[2]:
        st.write(day_score_summary(day_score))
        st.write(outdoor_summary(outdoor))
        st.write("Mood and health notes are comfort estimates only, not medical diagnosis.")

    with tabs[3]:
        if inputs["show_raw"]:
            st.json(parsed.raw)
        else:
            st.info("Enable raw API response in the sidebar to inspect the WeatherAI payload.")


def _fetch_weather(inputs: dict[str, Any]) -> dict[str, Any]:
    if inputs["use_demo"]:
        return copy.deepcopy(DEMO_WEATHER_PAYLOAD)

    client = WeatherAIClient(inputs["api_key"])
    return client.get_weather(
        lat=inputs["lat"],
        lon=inputs["lon"],
        days=inputs["days"],
        units="metric",
        ai=False,
        lang=DEFAULT_LANG,
    )


def _render_current_weather(current: WeatherSnapshot, units: str) -> None:
    st.markdown("### Current Weather")

    tiles = [
        ("Temperature", _format_temperature(current.temperature, units)),
        ("Humidity", _format_value(current.humidity, "%")),
        ("Rain chance", _format_value(current.rain_probability, "%")),
        ("Wind", _format_wind(current.wind_speed, units)),
        ("Condition", current.condition),
    ]
    for column, (label, value) in zip(st.columns(len(tiles)), tiles, strict=True):
        column.metric(label, value)


def _render_score_cards(
    day_score: Any,
    productivity: Any,
    outdoor: Any,
    sleep: Any,
    mood: Any,
    health: Any,
) -> None:
    st.markdown("### Human Impact")
    top = st.columns(3)
    with top[0]:
        _card("Overall Day Score", f"{day_score.score}/100", day_score.label, _score_accent(day_score.score))
        st.progress(day_score.score / 100)
    with top[1]:
        _card(
            "Productivity Window",
            productivity.label,
            f"Comfort score: {productivity.score}/100",
            _score_accent(productivity.score),
        )
    with top[2]:
        _card("Outdoor Comfort", outdoor.status, outdoor.reason, _outdoor_accent(outdoor.status))

    bottom = st.columns(3)
    with bottom[0]:
        _card("Sleep Comfort", sleep.status, sleep.reason, _sleep_accent(sleep.status))
    with bottom[1]:
        _card("Mood/Energy Impact", mood.level, mood.note, _level_accent(mood.level, low_is_good=True))
    with bottom[2]:
        _card("Health Discomfort", health.level, health.note, _level_accent(health.level, low_is_good=True))


def _render_report_header(
    location: str,
    location_detail: str,
    day_score: Any,
    productivity: Any,
    outdoor: Any,
    sleep: Any,
    is_demo: bool,
) -> None:
    demo_label = "Demo forecast" if is_demo else "Live forecast"
    st.markdown(
        f"""
        <section class="report-hero accent-{_score_accent(day_score.score)}">
            <div>
                <p class="eyebrow">{escape(demo_label)}</p>
                <h2>{escape(location)}</h2>
                <p class="report-subtitle">{escape(location_detail)} · {escape(day_score.label)}</p>
            </div>
            <div class="hero-metrics">
                <div><span>{day_score.score}</span><small>Day score</small></div>
                <div><span>{escape(productivity.label)}</span><small>Best focus</small></div>
                <div><span>{escape(outdoor.status)}</span><small>Outdoor</small></div>
                <div><span>{escape(sleep.status)}</span><small>Sleep</small></div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_windows(productivity: Any, outdoor: Any, sleep: Any, units: str) -> None:
    st.markdown("### Planning Windows")
    cols = st.columns(3)
    with cols[0]:
        _card("Focus Block", productivity.label, productivity.reason, _score_accent(productivity.score))
    with cols[1]:
        safe = ", ".join(outdoor.safe_windows) if outdoor.safe_windows else "No safe window found."
        _card("Outdoor Safe Windows", safe, outdoor.reason, _outdoor_accent(outdoor.status))
    with cols[2]:
        risky = ", ".join(outdoor.risky_windows) if outdoor.risky_windows else "No risky window found."
        _card("Outdoor Risk Windows", risky, outdoor.reason, _outdoor_accent(outdoor.status))

    sleep_detail = "Night averages unavailable."
    if sleep.avg_temperature is not None or sleep.avg_humidity is not None:
        sleep_detail = (
            f"Average night temperature: {_format_temperature(sleep.avg_temperature, units)}. "
            f"Average night humidity: {_format_value(sleep.avg_humidity, '%')}."
        )
    st.markdown(f'<div class="note-panel">{escape(sleep_detail)}</div>', unsafe_allow_html=True)


def _render_hourly_table(hourly: list[WeatherSnapshot], units: str) -> None:
    if not hourly:
        st.info("Hourly forecast data was not available in the API response.")
        return

    rows = [
        {
            "Time": format_snapshot_time(hour),
            "Temp": _format_temperature(hour.temperature, units),
            "Humidity": _format_value(hour.humidity, "%"),
            "Rain": _format_value(hour.rain_probability, "%"),
            "Wind": _format_wind(hour.wind_speed, units),
            "Focus score": score_productivity_hour(hour),
            "Outdoor": evaluate_outdoor_hour(hour),
        }
        for hour in hourly
    ]
    st.markdown("### Hourly Comfort Scan")
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_empty_state() -> None:
    st.markdown(
        """
        <section class="empty-state">
            <h2>Daily impact report ready</h2>
            <p>Select a forecast source from the sidebar and generate the report.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _card(title: str, value: str, body: str, accent: str = "blue") -> None:
    st.markdown(
        f"""
        <div class="daysense-card accent-{escape(accent)}">
            <div class="daysense-card-title">{escape(str(title))}</div>
            <div class="daysense-card-value">{escape(str(value))}</div>
            <div class="daysense-card-body">{escape(str(body))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_value(value: float | None, suffix: str) -> str:
    if value is None:
        return "N/A"
    if suffix == "%":
        return f"{value:.0f}%"
    return f"{value:.1f} {suffix}"


def _format_temperature(value_celsius: float | None, units: str) -> str:
    if value_celsius is None:
        return "N/A"
    if units == "imperial":
        return f"{(value_celsius * 9 / 5) + 32:.1f} F"
    return f"{value_celsius:.1f} C"


def _format_wind(value_kmh: float | None, units: str) -> str:
    if value_kmh is None:
        return "N/A"
    if units == "imperial":
        return f"{value_kmh * 0.621371:.1f} mph"
    return f"{value_kmh:.1f} km/h"


def _score_accent(score: int) -> str:
    if score >= 70:
        return "good"
    if score >= 50:
        return "warn"
    return "bad"


def _outdoor_accent(status: str) -> str:
    if status == "Good":
        return "good"
    if status == "Risky":
        return "warn"
    return "bad"


def _sleep_accent(status: str) -> str:
    if status == "Good":
        return "good"
    if status == "Medium":
        return "warn"
    return "bad"


def _level_accent(level: str, *, low_is_good: bool) -> str:
    if low_is_good and level == "Low":
        return "good"
    if level == "Medium":
        return "warn"
    if level == "High":
        return "bad"
    return "blue"


def _get_streamlit_secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        return ""
    return str(value).strip()


def _resolve_api_key() -> str:
    secret_key = _get_streamlit_secret("WEATHER_AI_API_KEY")
    if secret_key:
        return secret_key

    env_file_key = _get_dotenv_value("WEATHER_AI_API_KEY")
    if env_file_key:
        return env_file_key

    return WEATHER_AI_API_KEY.strip()


def _api_key_source(api_key: str) -> str:
    if not api_key:
        return ""
    if _get_streamlit_secret("WEATHER_AI_API_KEY") == api_key:
        return "Streamlit secrets"
    if _get_dotenv_value("WEATHER_AI_API_KEY") == api_key:
        return ".env"
    return "environment"


def _get_dotenv_value(name: str) -> str:
    dotenv_path = APP_PATH.parent / ".env"
    if not dotenv_path.exists():
        return ""

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")
    return ""


def _use_system_proxy() -> bool:
    return _get_dotenv_value("WEATHER_AI_USE_SYSTEM_PROXY").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #172033;
            --muted: #596579;
            --line: #d8dee9;
            --panel: #ffffff;
            --soft: #f5f7fb;
            --blue: #2f6fed;
            --teal: #0f8f8c;
            --amber: #b7791f;
            --violet: #6d5bd0;
            --green: #13795b;
            --red: #c24135;
        }
        .block-container {
            padding-top: 2rem;
            max-width: 1180px;
        }
        .app-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            border-bottom: 1px solid var(--line);
            padding-bottom: 1rem;
            margin-bottom: 1.25rem;
        }
        .app-header h1 {
            margin: 0;
            color: var(--ink);
            font-size: 2.4rem;
            line-height: 1.05;
            letter-spacing: 0;
        }
        .eyebrow {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 760;
            letter-spacing: 0;
            text-transform: uppercase;
            margin: 0 0 0.35rem 0;
        }
        .header-chip {
            border: 1px solid var(--line);
            border-radius: 999px;
            color: var(--muted);
            padding: 0.45rem 0.75rem;
            font-size: 0.86rem;
            white-space: nowrap;
        }
        .report-hero {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1.2rem;
            margin-bottom: 1.2rem;
            background: var(--soft);
            border-left-width: 6px;
        }
        .report-hero h2 {
            margin: 0;
            color: var(--ink);
            font-size: 1.7rem;
            letter-spacing: 0;
        }
        .report-subtitle {
            color: var(--muted);
            margin: 0.35rem 0 1rem 0;
        }
        .hero-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
        }
        .hero-metrics div {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.8rem;
            min-height: 76px;
        }
        .hero-metrics span {
            display: block;
            color: var(--ink);
            font-size: 1.2rem;
            font-weight: 760;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }
        .hero-metrics small {
            color: var(--muted);
            display: block;
            margin-top: 0.25rem;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.75rem;
            margin-bottom: 1.25rem;
        }
        .metric-tile {
            background: var(--panel);
            border: 1px solid var(--line);
            border-left-width: 5px;
            border-radius: 8px;
            padding: 0.85rem;
            min-height: 96px;
        }
        .metric-label {
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.35rem;
        }
        .metric-value {
            color: var(--ink);
            font-size: 1.3rem;
            font-weight: 760;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }
        .daysense-card {
            border: 1px solid #d8dee9;
            border-left-width: 5px;
            border-radius: 8px;
            padding: 1rem;
            min-height: 150px;
            background: #ffffff;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
            margin-bottom: 1rem;
        }
        .daysense-card-title {
            color: #42526b;
            font-size: 0.86rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0;
            margin-bottom: 0.45rem;
        }
        .daysense-card-value {
            color: #172033;
            font-size: 1.45rem;
            font-weight: 750;
            line-height: 1.25;
            overflow-wrap: anywhere;
            margin-bottom: 0.5rem;
        }
        .daysense-card-body {
            color: #4b5565;
            font-size: 0.95rem;
            line-height: 1.45;
        }
        .accent-blue { border-left-color: var(--blue); }
        .accent-teal { border-left-color: var(--teal); }
        .accent-amber { border-left-color: var(--amber); }
        .accent-violet { border-left-color: var(--violet); }
        .accent-gray { border-left-color: #7b8794; }
        .accent-good { border-left-color: var(--green); }
        .accent-warn { border-left-color: var(--amber); }
        .accent-bad { border-left-color: var(--red); }
        .recommendation {
            border: 1px solid #b7d8ca;
            border-left: 5px solid var(--green);
            border-radius: 8px;
            background: #f1fbf6;
            color: var(--ink);
            padding: 1rem;
            font-size: 1.05rem;
            line-height: 1.5;
            margin-bottom: 1rem;
        }
        .note-panel,
        .empty-state {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--soft);
            padding: 1rem;
            color: var(--muted);
        }
        .empty-state {
            min-height: 220px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            color: var(--ink);
        }
        .empty-state h2 {
            margin: 0 0 0.35rem 0;
            font-size: 1.5rem;
            letter-spacing: 0;
        }
        .empty-state p {
            margin: 0;
            color: var(--muted);
        }
        @media (max-width: 860px) {
            .app-header,
            .hero-metrics,
            .metric-grid {
                display: block;
            }
            .header-chip,
            .hero-metrics div,
            .metric-tile {
                margin-top: 0.75rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _is_running_with_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ == "__main__":
    if _is_running_with_streamlit():
        main()
    else:
        _launch_with_streamlit()
