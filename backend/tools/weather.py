"""
Tool 2: Weather Info
Uses OpenWeatherMap API to get current weather for any city.
Name: get_weather
Description: Returns current weather conditions for a given city.
Parameters:
  - city (str): City name to get the weather for (e.g., "Medellín", "Bogotá").
"""

import os
import requests
from langchain.tools import tool


def get_weather_keyless(city: str) -> str:
    """Fetch weather information from Open-Meteo keyless API."""
    try:
        # Step 1: Geocoding
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=es&format=json"
        geo_resp = requests.get(geocode_url, timeout=8)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return f"City '{city}' not found. Please check the spelling."

        loc = geo_data["results"][0]
        lat = loc["latitude"]
        lon = loc["longitude"]
        name = loc.get("name", city)
        country = loc.get("country", "")

        # Step 2: Get current weather
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_resp = requests.get(weather_url, timeout=8)
        w_resp.raise_for_status()
        w_data = w_resp.json()

        current = w_data.get("current_weather", {})
        temp = current.get("temperature", "N/A")
        wind_speed = current.get("windspeed", "N/A")
        weathercode = current.get("weathercode", 0)

        descriptions = {
            0: "Despejado",
            1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Cubierto",
            45: "Niebla", 48: "Niebla de escarcha",
            51: "Llovizna ligera", 53: "Llovizna moderada", 55: "Llovizna densa",
            61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia fuerte",
            71: "Nieve ligera", 73: "Nieve moderada", 75: "Nieve fuerte",
            77: "Granos de nieve",
            80: "Lloviznas ligeras", 81: "Lloviznas moderadas", 82: "Lloviznas violentas",
            85: "Chubascos de nieve ligeros", 86: "Chubascos de nieve fuertes",
            95: "Tormenta eléctrica", 96: "Tormenta con granizo ligero", 99: "Tormenta con granizo fuerte"
        }
        desc = descriptions.get(weathercode, "Desconocido")

        return (
            f"Weather in {name}, {country} (Free Open-Meteo):\n"
            f"  Condition: {desc}\n"
            f"  Temperature: {temp}°C\n"
            f"  Wind speed: {wind_speed} km/h"
        )
    except Exception as e:
        print(f"[Weather Open-Meteo error] {e}")
        return f"Weather service error: {str(e)}"


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
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "es",
        }
        response = requests.get(url, params=params, timeout=8)

        if response.status_code == 401:
            print("[Weather] Invalid OPENWEATHER_API_KEY, falling back to Open-Meteo.")
            return get_weather_keyless(city)

        if response.status_code == 404:
            return f"City '{city}' not found. Please check the spelling."

        if not response.ok:
            print(f"[Weather] OpenWeatherMap error {response.status_code}, falling back to Open-Meteo.")
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

    except requests.exceptions.Timeout:
        print("[Weather] OpenWeatherMap timeout, falling back to Open-Meteo.")
        return get_weather_keyless(city)
    except requests.exceptions.RequestException as e:
        print(f"[Weather] OpenWeatherMap request error: {e}, falling back to Open-Meteo.")
        return get_weather_keyless(city)
    except Exception as e:
        print(f"[Weather] Unexpected error: {e}, falling back to Open-Meteo.")
        return get_weather_keyless(city)
