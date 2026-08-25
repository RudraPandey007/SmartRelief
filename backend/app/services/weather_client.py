"""
Weather Client — calls external weather API with caching and rate limiting.

Features:
  - TTL cache keyed by village_id + rounded coordinates (avoids repeated calls)
  - Hard call cap per minute (protects shared API key)
  - Graceful degradation: returns None if API fails or is capped
"""
import logging
import time
from typing import Optional
from cachetools import TTLCache
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache setup
# ---------------------------------------------------------------------------
_settings = get_settings()
_cache = TTLCache(maxsize=100, ttl=_settings.CACHE_TTL_SECONDS)


class WeatherCallCounter:
    """Simple token-bucket counter for weather API calls."""
    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.calls: list[float] = []

    def can_call(self) -> bool:
        now = time.time()
        # Remove calls older than 60 seconds
        self.calls = [t for t in self.calls if now - t < 60]
        return len(self.calls) < self.max_per_minute

    def record_call(self):
        self.calls.append(time.time())

    def calls_in_last_minute(self) -> int:
        now = time.time()
        return sum(1 for t in self.calls if now - t < 60)


_counter = WeatherCallCounter(_settings.MAX_WEATHER_CALLS_PER_MINUTE)


def _cache_key(village_id: str, lat: float, lon: float) -> str:
    """Generate cache key from village_id + rounded coordinates."""
    return f"{village_id}:{round(lat, 2)}:{round(lon, 2)}"


async def fetch_weather(
    village_id: str,
    latitude: float,
    longitude: float,
) -> Optional[dict]:
    """
    Fetch current weather data for a location.

    Returns dict with rainfall_mm or None if unavailable.
    """
    settings = get_settings()

    # Skip if no API configured
    if not settings.WEATHER_API_KEY or settings.WEATHER_API_KEY.startswith("REPLACE"):
        logger.info("Weather API not configured, using seed data")
        return None

    # Check cache first
    key = _cache_key(village_id, latitude, longitude)
    if key in _cache:
        logger.debug(f"Cache hit for weather: {key}")
        return _cache[key]

    # Check call cap
    if not _counter.can_call():
        logger.warning(f"Weather API call cap reached ({_counter.calls_in_last_minute()} calls/min)")
        return None

    try:
        _counter.record_call()

        # Generic weather API call (provider-agnostic)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.WEATHER_API_BASE_URL}/current",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "appid": settings.WEATHER_API_KEY,
                    "units": "metric",
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract rainfall (provider-specific parsing would go here)
            result = {
                "rainfall_mm": data.get("rain", {}).get("1h", 0.0),
                "temperature": data.get("main", {}).get("temp", 0.0),
                "humidity": data.get("main", {}).get("humidity", 0),
            }

            _cache[key] = result
            return result

    except httpx.HTTPStatusError as e:
        logger.error(f"Weather API HTTP error: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Weather API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Weather API unexpected error: {e}")
        return None


def get_weather_sync(
    village_id: str,
    latitude: float,
    longitude: float,
) -> Optional[dict]:
    """
    Synchronous wrapper for weather fetch.
    Returns None if unavailable (graceful degradation).
    """
    settings = get_settings()

    # Skip if no API configured
    if not settings.WEATHER_API_KEY or settings.WEATHER_API_KEY.startswith("REPLACE"):
        return None

    # Check cache first
    key = _cache_key(village_id, latitude, longitude)
    if key in _cache:
        return _cache[key]

    # Check call cap
    if not _counter.can_call():
        logger.warning("Weather API call cap reached")
        return None

    try:
        _counter.record_call()

        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{settings.WEATHER_API_BASE_URL}/current",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "appid": settings.WEATHER_API_KEY,
                    "units": "metric",
                },
            )
            response.raise_for_status()
            data = response.json()

            result = {
                "rainfall_mm": data.get("rain", {}).get("1h", 0.0),
                "temperature": data.get("main", {}).get("temp", 0.0),
                "humidity": data.get("main", {}).get("humidity", 0),
            }

            _cache[key] = result
            return result

    except Exception as e:
        logger.error(f"Weather API sync call failed: {e}")
        return None
