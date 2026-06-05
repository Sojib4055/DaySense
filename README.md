# DaySense AI

**Weather-Based Human Impact Intelligence**

DaySense AI is a Streamlit web app that uses WeatherAI forecast data to explain how weather may affect a user's day. Instead of only displaying raw values like temperature, humidity, wind, and rain probability, the app converts those values into human-centered daily insights.

## Project Snapshot

| Area | Used In This Project |
| --- | --- |
| Primary language | Python |
| UI framework | Streamlit |
| API client | Requests |
| Environment handling | python-dotenv and `.env` |
| Main external API | WeatherAI API v1 |
| Location fallback | OpenStreetMap Nominatim reverse geocoding |
| Intelligence model | Rule-based predictive impact engine |
| ML/LLM usage | No trained ML model or LLM; explainable scoring rules are used |
| Deployment target | Streamlit locally, Hugging Face Spaces or Render for hosting |

## Challenge Fit

The challenge asks for a simple implementation, predictive experiment, or intelligent feature that integrates a developer-platform API and turns data into intelligent insights.

DaySense AI satisfies this by:

- Calling WeatherAI API with user latitude, longitude, forecast days, units, and API key.
- Parsing live current, daily, and hourly weather forecast data.
- Running a custom rule-based intelligence layer over that data.
- Producing predictive daily-life insights: productivity, outdoor risk, sleep comfort, mood/energy impact, health discomfort, and a final plan.
- Showing both clean human output and raw API data for transparency.

## What The App Does

DaySense AI answers:

```text
How will this weather affect my day?
```

It generates:

- Overall Day Score out of 100.
- Best productivity or study window.
- Outdoor comfort status and risky time windows.
- Sleep comfort estimate for night hours.
- Mood and energy comfort note.
- Weather-related health discomfort note.
- Final daily recommendation.
- Exact location label and coordinates.
- Optional raw API response viewer.

## User Inputs

The sidebar contains the app inputs.

| Input | What To Enter | Notes |
| --- | --- | --- |
| Latitude | Example: `23.8103` or `40.730610` | Required for live WeatherAI request. |
| Longitude | Example: `90.4125` or `-73.935242` | Required for live WeatherAI request. |
| Forecast days | `1` to `7` | Follows the Free-plan-friendly MVP limit. |
| Display units | `metric` or `imperial` | Scoring uses metric internally; display is converted if needed. |
| Purpose | General, Work, Study, Travel, Outdoor work, Exercise, Sleep planning | Used to tailor final advice. |
| WeatherAI API key | Optional sidebar fallback | Prefer `.env`; do not commit real keys. |
| Demo forecast | On or off | On uses bundled sample data and ignores live latitude/longitude. |
| Show raw API response | On or off | Shows the WeatherAI JSON in the Raw Data tab. |

## App Outputs

After clicking **Generate report**, the app shows:

| Output Section | Meaning |
| --- | --- |
| Report header | Live/demo status, resolved location, exact coordinates, main summary cards. |
| Current Weather | Temperature, humidity, rain chance, wind, and condition. |
| Human Impact | Day score, productivity window, outdoor comfort, sleep comfort, mood/energy, health discomfort. |
| Final Recommendation | One practical daily plan for the selected purpose. |
| Hourly Windows tab | Safe/risky outdoor windows and hourly comfort scan. |
| Methodology tab | Explanation of why the app scored the day that way. |
| Raw Data tab | API JSON response when enabled. |

## Project Structure

```text
DaySense/
|
|-- app.py                    Streamlit UI and app flow
|-- D.py                      Compatibility launcher
|-- config.py                 Environment variables and constants
|-- weather_api.py            WeatherAI API client and error handling
|-- data_parser.py            WeatherAI response normalization
|-- impact_engine.py          Rule-based impact scoring
|-- recommendation_engine.py  Daily advice generation
|-- location_resolver.py      Better location display from coordinates
|-- demo_data.py              Local demo payload without API calls
|-- requirements.txt          Python dependencies
|-- .env.example              Safe environment template
|-- .gitignore                Keeps secrets and generated files out of Git
|-- screenshots/              Screenshot folder for submission assets
```

## Data Flow

```text
User Input
  -> WeatherAI API Request
  -> JSON Response
  -> Weather Data Parser
  -> DaySense Impact Engine
  -> Recommendation Engine
  -> Streamlit Report
```

## APIs Used

### WeatherAI API v1

Main endpoint used by the MVP:

```text
GET https://api.weather-ai.co/v1/weather
```

The app sends:

```text
lat=<latitude>
lon=<longitude>
days=<1-7>
units=metric
ai=false
lang=en
```

`ai=false` is intentional. DaySense AI uses WeatherAI as the data layer and applies its own local intelligence layer for scoring and recommendations.

### OpenStreetMap Nominatim

WeatherAI may return a broad location label such as `US`. To make the report more useful, `location_resolver.py` reverse-geocodes the latitude and longitude when the API location is not specific enough.

Example:

```text
36.778259, -119.417931
-> Fresno County, California, United States
```

## Intelligence Model

This project uses an explainable rule-based predictive model. It is not a trained machine-learning model.

The model is split into focused components:

- Overall day scoring.
- Hourly productivity scoring.
- Outdoor comfort classification.
- Sleep comfort classification.
- Mood and energy comfort estimate.
- Health discomfort estimate.
- Final recommendation generation.

This approach was chosen because it is:

- Easy to debug.
- Easy to explain in a challenge submission.
- Directly connected to WeatherAI forecast fields.
- Reliable for an MVP.

## Scoring Method

The overall day score starts at `100` and subtracts penalties.

| Weather Factor | Rule | Penalty |
| --- | --- | --- |
| Temperature | `>= 35 C` | `-20` |
| Temperature | `>= 30 C` | `-10` |
| Humidity | `>= 85%` | `-15` |
| Humidity | `>= 75%` | `-8` |
| Rain probability | `>= 70%` | `-20` |
| Rain probability | `>= 40%` | `-10` |
| Wind speed | `>= 35 km/h` | `-10` |
| Wind speed | `>= 25 km/h` | `-5` |
| Cloud cover | `>= 85%` | `-5` |

Score labels:

| Score | Label |
| --- | --- |
| `85-100` | Excellent day |
| `70-84` | Good day |
| `50-69` | Moderate day |
| `30-49` | Uncomfortable day |
| `0-29` | Poor day |

## Setup Step By Step

### 1. Open the project folder

```powershell
cd E:\Practice\DaySense
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 5. Create the `.env` file

```powershell
Copy-Item .env.example .env
```

### 6. Add your WeatherAI API key

Open `.env` and set:

```env
WEATHER_AI_API_KEY=wai_your_real_key_here
WEATHER_AI_BASE_URL=https://api.weather-ai.co
WEATHER_AI_UNITS=metric
WEATHER_AI_LANG=en
WEATHER_AI_USE_SYSTEM_PROXY=false
```

Do not commit `.env`.

### 7. Run the app

Recommended command:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Alternative command:

```powershell
python3 app.py
```

The app includes a launcher that redirects `python3 app.py` to the local `.venv` Streamlit runner when possible.

### 8. Open the browser

Streamlit usually opens:

```text
http://localhost:8501
```

## How To Use The App

### Demo mode

Use this when you do not want to call the live API.

1. Turn **Demo forecast** on.
2. Click **Generate report**.
3. The app shows bundled sample weather data.

Demo mode ignores latitude, longitude, and API key.

### Live mode

Use this for real WeatherAI results.

1. Add a valid `WEATHER_AI_API_KEY` in `.env`.
2. Restart Streamlit.
3. Confirm the sidebar says `API key loaded from .env.`
4. Confirm the sidebar says `WeatherAI network: direct connection.`
5. Turn **Demo forecast** off.
6. Enter latitude and longitude.
7. Click **Generate report**.

## Requirements

```text
streamlit>=1.58,<2
requests>=2.34,<3
python-dotenv>=1.2,<2
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'streamlit'`

You are probably using a different Python interpreter than `.venv`.

Use:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

### `ModuleNotFoundError: No module named 'dotenv'`

Install requirements into the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### API key input still appears

The app did not load `.env`.

Check that `.env` is in:

```text
E:\Practice\DaySense\.env
```

Then restart Streamlit.

### Proxy error with `127.0.0.1:9`

Your Windows environment may have broken proxy variables. This project bypasses proxy settings by default with:

```env
WEATHER_AI_USE_SYSTEM_PROXY=false
```

If you intentionally need a proxy, set it to `true`.

### Location shows only `US`

WeatherAI may return a country-only location label. The app now reverse-geocodes latitude and longitude to show a better location and always includes exact coordinates.

## Security Notes

- Never commit `.env`.
- Never paste a real API key into a public README, issue, commit, or chat.
- If a key is exposed, revoke it and generate a new one from the WeatherAI dashboard.
- `.env.example` must contain only placeholder values.

## Deployment

### Hugging Face Spaces

1. Push the project to GitHub without `.env`.
2. Create a new Hugging Face Space.
3. Select Streamlit as the SDK.
4. Add `WEATHER_AI_API_KEY` as a Space secret.
5. Add `WEATHER_AI_USE_SYSTEM_PROXY=false` as a Space secret or environment variable.
6. Deploy.
7. Add the live URL and screenshot to this README.

### Render

Use a Streamlit-compatible start command:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

Add environment variables in the Render dashboard.

## Limitations

- The app depends on WeatherAI response fields being available.
- `data_parser.py` supports multiple common weather JSON shapes because the implementation document did not include a complete example response.
- Mood, energy, sleep, and health outputs are comfort estimates, not medical advice.
- The app intentionally does not include login, registration, or user history for the MVP.

## Future Improvements

- Add charts for hourly temperature, rain probability, and comfort score.
- Add WeatherAI `/v1/usage` quota monitoring.
- Add `/v1/weather-geo` for automatic location detection.
- Add saved user profiles and preferred locations.
- Add more purpose-specific recommendations.
- Add deployment screenshot in `screenshots/demo.png`.

## Source

- WeatherAI API documentation: https://weather-ai.co/docs
- DaySense AI implementation documentation PDF
- Documentation checked on June 5, 2026
