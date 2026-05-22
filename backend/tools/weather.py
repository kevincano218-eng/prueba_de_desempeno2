"""
Tool 2: Weather Info
Uses OpenWeatherMap API to get current weather for any city.
Name: get_weather
Description: Returns current weather conditions for a given city.
Parameters:
  - city (str): City name to get the weather for (e.g., "Medellín", "Bogotá").
"""

import os
import time
import requests
from langchain.tools import tool


_weather_cache: dict = {}

# ---------------------------------------------------------------------------
# Fallback 3: wttr.in (gratuito, sin API key, respeta rate limits)
# ---------------------------------------------------------------------------
def _fetch_wttr(city: str) -> str | None:
    """Fetch weather from wttr.in as last-resort fallback."""
    try:
        resp = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        cc = data.get("current_condition", [{}])[0]
        if not cc:
            return None
        temp = cc.get("temp_C", "N/A")
        desc = cc.get("lang_es", [{}])[0].get("value",
               cc.get("weatherDesc", [{}])[0].get("value", "N/A"))
        wind = cc.get("windspeedKmph", "N/A")
        humidity = cc.get("humidity", "N/A")
        return (
            f"Weather in {city} (wttr.in):\n"
            f"  Condition: {desc}\n"
            f"  Temperature: {temp}°C\n"
            f"  Humidity: {humidity}%\n"
            f"  Wind speed: {wind} km/h"
        )
    except Exception as e:
        print(f"[Weather wttr.in error] {e}")
        return None


# ---------------------------------------------------------------------------
# Fallback 2: Open-Meteo (gratuito, sin API key)
# ---------------------------------------------------------------------------
def _fetch_openmeteo(city: str, lat: float, lon: float, name: str, country: str) -> str | None:
    """Fetch weather from Open-Meteo. Returns None on 429 so caller can try next fallback."""
    now = time.time()
    cached = _weather_cache.get(city)
    if cached and now - cached["time"] < 120:
        return cached["result"] if not cached["result"].startswith("__RATE_LIMITED__") else None

    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_resp = requests.get(weather_url, timeout=8)

        if w_resp.status_code == 429:
            _weather_cache[city] = {"result": "__RATE_LIMITED__", "time": now}
            return None

        w_resp.raise_for_status()
        w_data = w_resp.json()

        current = w_data.get("current_weather", {})
        temp = current.get("temperature", "N/A")
        wind_speed = current.get("windspeed", "N/A")
        weathercode = current.get("weathercode", 0)

        descriptions = {
            0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Cubierto",
            45: "Niebla", 48: "Niebla de escarcha",
            51: "Llovizna ligera", 53: "Llovizna moderada", 55: "Llovizna densa",
            61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia fuerte",
            71: "Nieve ligera", 73: "Nieve moderada", 75: "Nieve fuerte", 77: "Granos de nieve",
            80: "Lloviznas ligeras", 81: "Lloviznas moderadas", 82: "Lloviznas violentas",
            85: "Chubascos de nieve ligeros", 86: "Chubascos de nieve fuertes",
            95: "Tormenta eléctrica", 96: "Tormenta con granizo ligero", 99: "Tormenta con granizo fuerte"
        }
        desc = descriptions.get(weathercode, "Desconocido")

        result = (
            f"Weather in {name}, {country} (Open-Meteo):\n"
            f"  Condition: {desc}\n"
            f"  Temperature: {temp}°C\n"
            f"  Wind speed: {wind_speed} km/h"
        )
        _weather_cache[city] = {"result": result, "time": now}
        return result

    except Exception as e:
        print(f"[Weather Open-Meteo error] {e}")
        return None


def _geocode_openmeteo(city: str) -> tuple:
    """Geocode a city using Open-Meteo. Returns (lat, lon, name, country) or None."""
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=es&format=json"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 429:
            return None
        resp.raise_for_status()
        data = resp.json()
        if not data.get("results"):
            return None
        loc = data["results"][0]
        return (loc["latitude"], loc["longitude"], loc.get("name", city), loc.get("country", ""))
    except Exception as e:
        print(f"[Weather geocode error] {e}")
        return None


def get_weather_keyless(city: str) -> str:
    """Try Open-Meteo first, then fall back to wttr.in."""
    geo = _geocode_openmeteo(city)
    if geo:
        result = _fetch_openmeteo(city, *geo)
        if result:
            return result
    fallback = _fetch_wttr(city)
    if fallback:
        return fallback
    return "Weather service is temporarily unavailable. Please try again later."


# ---------------------------------------------------------------------------
# Fallback 1: OpenWeatherMap (requiere API key)
# ---------------------------------------------------------------------------
@tool
def get_weather(city: str) -> str:
    """
    Get the current weather conditions for any city in the world.
    Use this when the user asks about the weather, temperature, rain,
    or climate conditions in a specific city or location.

    Args:
        city: Name of the city to check (e.g., "Medellín", "New York", "Madrid").

    Returns:
        A formatted string describing current weather conditions.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return get_weather_keyless(city)

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": api_key, "units": "metric", "lang": "es"}
        response = requests.get(url, params=params, timeout=8)

        if not response.ok:
            print(f"[Weather] OpenWeatherMap error {response.status_code}, falling back.")
            return get_weather_keyless(city)

        data = response.json()
        name = data.get("name", city)
        country = data.get("sys", {}).get("country", "")
        temp = data.get("main", {}).get("temp", "N/A")
        feels_like = data.get("main", {}).get("feels_like", "N/A")
        humidity = data.get("main", {}).get("humidity", "N/A")
        description = data.get("weather", [{}])[0].get("description", "N/A").capitalize()
        wind_speed = data.get("wind", {}).get("speed", "N/A")
        visibility = data.get("visibility", 0)
        visibility_km = round(visibility / 1000, 1) if visibility else "N/A"

        return (
            f"Weather in {name}, {country}:\n"
            f"  Condition: {description}\n"
            f"  Temperature: {temp}°C (feels like {feels_like}°C)\n"
            f"  Humidity: {humidity}%\n"
            f"  Wind speed: {wind_speed} m/s\n"
            f"  Visibility: {visibility_km} km"
        )

    except Exception as e:
        print(f"[Weather] OpenWeatherMap error: {e}, falling back.")
        return get_weather_keyless(city)
