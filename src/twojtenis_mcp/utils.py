"""Utility functions for TwojTenis MCP server."""

import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

url_regex = re.compile(r"/([^/]+)\.\w+$")
date_regex = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
time_regex = re.compile(r"^\d{2}:\d{2}$")


def validate_date(date_str: str) -> bool:
    """Validate date format (DD.MM.YYYY).

    Args:
        date_str: Date string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        if not re.match(date_regex, date_str):
            return False

        day, month, year = map(int, date_str.split("."))

        # Basic validation
        if not (1 <= day <= 31):
            return False
        if not (1 <= month <= 12):
            return False
        if not (2020 <= year <= 2030):  # Reasonable year range
            return False

        # Try to create a date object to validate
        datetime(year=year, month=month, day=day)
        return True

    except (ValueError, AttributeError):
        return False


def validate_time(time_str: str) -> bool:
    """Validate time format (HH:MM).

    Args:
        time_str: Time string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        if not re.match(time_regex, time_str):
            return False

        hour, minute = map(int, time_str.split(":"))

        # Basic validation
        if not (0 <= hour <= 23):
            return False
        if not (0 <= minute <= 59):
            return False

        # Check if it's a valid slot (usually on the hour or half hour)
        if minute not in [0, 30]:
            return False

        return True

    except (ValueError, AttributeError):
        return False


def format_date_for_display(date_str: str) -> str:
    """Format date for display (DD.MM.YYYY -> more readable format).

    Args:
        date_str: Date string in DD.MM.YYYY format

    Returns:
        Formatted date string
    """
    try:
        if not validate_date(date_str):
            return date_str

        day, month, year = map(int, date_str.split("."))
        date_obj = datetime(year=year, month=month, day=day)

        # Format as "Day Month Year" (e.g., "24 September 2025")
        return date_obj.strftime("%d %B %Y")

    except (ValueError, AttributeError):
        return date_str


def format_time_for_display(time_str: str) -> str:
    """Format time for display (HH:MM -> more readable format).

    Args:
        time_str: Time string in HH:MM format

    Returns:
        Formatted time string
    """
    try:
        if not validate_time(time_str):
            return time_str

        hour, minute = map(int, time_str.split(":"))

        # Convert to 12-hour format with AM/PM
        if hour == 0:
            return f"12:{minute:02d} AM"
        elif hour < 12:
            return f"{hour}:{minute:02d} AM"
        elif hour == 12:
            return f"12:{minute:02d} PM"
        else:
            return f"{hour - 12}:{minute:02d} PM"

    except (ValueError, AttributeError):
        return time_str


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for retrying functions on failure.

    Args:
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
    """
    import asyncio

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay * (2**attempt))  # Exponential backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed")
            if last_exception is not None:
                raise last_exception

        return wrapper

    return decorator


def extract_id_from_url(url: str) -> str | None:
    """Parse URL to extract ID from the file name (without extension)"""
    loc = re.search(url_regex, url)
    if not loc:
        return None
    id = loc.group(1)  # type: ignore
    return str(id)
