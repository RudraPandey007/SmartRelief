"""Gemini client — calls Google Gemini for natural-language plan summaries."""
import hashlib
import logging
import time
from typing import Optional
from cachetools import TTLCache
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Lazy-init: avoids Vercel cold-start crashes from early env var access.
_cache: Optional[TTLCache] = None
_counter: Optional["GeminiCallCounter"] = None


class GeminiCallCounter:
    """Simple token-bucket counter for Gemini API calls."""
    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.calls: list[float] = []

    def can_call(self) -> bool:
        now = time.time()
        self.calls = [t for t in self.calls if now - t < 60]
        return len(self.calls) < self.max_per_minute

    def record_call(self):
        self.calls.append(time.time())

    def calls_in_last_minute(self) -> int:
        now = time.time()
        return sum(1 for t in self.calls if now - t < 60)


def _get_lazy_state():
    """Return (cache, counter), initializing them on first call."""
    global _cache, _counter
    if _cache is None or _counter is None:
        settings = get_settings()
        _cache = TTLCache(maxsize=50, ttl=settings.CACHE_TTL_SECONDS)
        _counter = GeminiCallCounter(settings.MAX_GEMINI_CALLS_PER_MINUTE)
    return _cache, _counter


def _plan_hash(plan_text: str) -> str:
    """Generate a stable hash for plan text to use as cache key."""
    return hashlib.sha256(plan_text.encode()).hexdigest()[:16]


async def generate_plan_summary(plan_data: dict) -> Optional[str]:
    """Generate a Gemini summary of the plan. Returns None if unavailable."""
    settings = get_settings()

    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("REPLACE"):
        logger.info("Gemini API not configured, using rule-based summary")
        return None

    prompt = _build_summary_prompt(plan_data)

    cache, counter = _get_lazy_state()

    cache_key = _plan_hash(prompt)
    if cache_key in cache:
        logger.debug(f"Cache hit for Gemini summary: {cache_key}")
        return cache[cache_key]

    if not counter.can_call():
        logger.warning(f"Gemini API call cap reached ({counter.calls_in_last_minute()} calls/min)")
        return None

    try:
        counter.record_call()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent",
                params={"key": settings.GEMINI_API_KEY},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 500,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            summary = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            if summary:
                cache[cache_key] = summary
                return summary
            else:
                logger.warning("Gemini returned empty response")
                return None

    except httpx.HTTPStatusError as e:
        logger.error(f"Gemini API HTTP error: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Gemini API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Gemini API unexpected error: {e}")
        return None


def generate_plan_summary_sync(plan_data: dict) -> Optional[str]:
    """Sync version of generate_plan_summary."""
    settings = get_settings()

    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("REPLACE"):
        return None

    prompt = _build_summary_prompt(plan_data)

    cache, counter = _get_lazy_state()

    cache_key = _plan_hash(prompt)
    if cache_key in cache:
        return cache[cache_key]

    if not counter.can_call():
        logger.warning("Gemini API call cap reached")
        return None

    try:
        counter.record_call()

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent",
                params={"key": settings.GEMINI_API_KEY},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 500,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            summary = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            if summary:
                cache[cache_key] = summary
                return summary
            return None

    except Exception as e:
        logger.error(f"Gemini sync call failed: {e}")
        return None


def _build_summary_prompt(plan_data: dict) -> str:
    """Build a structured prompt for Gemini to summarize the evacuation plan."""
    village = plan_data.get("village_name", "Unknown")
    district = plan_data.get("district", "Unknown")
    risk = plan_data.get("risk_classification", "unknown")
    hazard = plan_data.get("hazard_score", 0)
    vuln = plan_data.get("vulnerability_score", 0)
    affected = plan_data.get("affected_families", 0)
    allocated = plan_data.get("total_families_allocated", 0)
    unallocated = plan_data.get("unallocated_families", 0)
    destinations = plan_data.get("ranked_destinations", [])

    dest_summary = []
    for d in destinations[:3]:  # Top 3
        dest_summary.append(
            f"- {d.get('name', 'Unknown')} ({d.get('type', 'village')}): "
            f"rank #{d.get('rank', 0)}, score {d.get('weighted_total', 0):.2f}, "
            f"{d.get('families_allocated', 0)} families allocated"
        )

    prompt = f"""You are an emergency evacuation planning assistant. Summarize this evacuation plan in 2-3 clear sentences for government officials:

Source Village: {village}, {district}
Risk Level: {risk.upper()} (hazard: {hazard:.2f}, vulnerability: {vuln:.2f})
Affected Families: {affected}
Families Allocated: {allocated}
Unallocated: {unallocated}

Top Destinations:
{chr(10).join(dest_summary) if dest_summary else 'None available'}

Provide a concise, actionable summary focusing on safety and logistics. Do not use markdown formatting."""

    return prompt
