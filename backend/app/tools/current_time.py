from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIMEZONE_ALIASES = {
    "asia/kolkata": "Asia/Kolkata",
    "india": "Asia/Kolkata",
    "indian time": "Asia/Kolkata",
    "ist": "Asia/Kolkata",
    "utc": "UTC",
    "gmt": "UTC",
    "london": "Europe/London",
    "uk": "Europe/London",
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "america/new_york": "America/New_York",
    "california": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "pst": "America/Los_Angeles",
    "america/los_angeles": "America/Los_Angeles",
}


def resolve_timezone_name(value: str | None) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return "UTC"

    normalized = candidate.lower().replace("-", " ").replace("_", " ")
    if normalized in TIMEZONE_ALIASES:
        return TIMEZONE_ALIASES[normalized]

    slash_form = candidate.strip().replace(" ", "_")
    if "/" in slash_form:
        return slash_form

    return candidate


async def get_current_time(arguments: dict[str, str]) -> str:
    timezone_name = resolve_timezone_name(arguments.get("timezone"))
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
        timezone_name = "UTC"

    now = datetime.now(zone)
    return (
        f"The current time in {timezone_name} is "
        f"{now.strftime('%A, %B %d, %Y at %I:%M %p %Z')}."
    )
