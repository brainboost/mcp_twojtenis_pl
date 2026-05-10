from __future__ import annotations

from datetime import date as _date
from typing import Any

from .models import derive_sport

SLOT_MINUTES = 30
WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _parse_hms(s: str) -> int:
    """Parse 'HH:MM' or 'HH:MM:SS' into total minutes since midnight."""
    parts = s.split(":")
    if len(parts) < 2:
        raise ValueError(f"unrecognized time {s!r}")
    return int(parts[0]) * 60 + int(parts[1])


def _fmt(minutes: int) -> str:
    """Format minutes-since-midnight as 'HH:MM'."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _slots_for_window(start_min: int, end_min: int) -> list[tuple[int, int]]:
    """Generate 30-minute (start, end) slot tuples within [start_min, end_min)."""
    out: list[tuple[int, int]] = []
    cursor = start_min
    while cursor + SLOT_MINUTES <= end_min:
        out.append((cursor, cursor + SLOT_MINUTES))
        cursor += SLOT_MINUTES
    return out


def _interval_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _exclude_applies_to(exclude: dict[str, Any], location_id: str) -> bool:
    """Excludes may target one location, a list, or be club-wide. Treat unscoped as club-wide."""
    if "locationId" in exclude:
        return exclude["locationId"] == location_id
    if "locations" in exclude and isinstance(exclude["locations"], list):
        return location_id in exclude["locations"]
    return True


def _booking_minutes(b: dict[str, Any]) -> tuple[int, int] | None:
    start = b.get("startTime") or b.get("startHour")
    end = b.get("endTime") or b.get("endHour")
    if not start or not end:
        return None
    return _parse_hms(start), _parse_hms(end)


def build_availability(
    *,
    iso_date: str,
    locations: list[dict[str, Any]],
    open_hours: dict[str, Any],
    bookings: list[dict[str, Any]],
    excludes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a per-court availability grid for one date.

    Each entry: {location_id, location_name, sport, slots: [{start, end, available}]}.
    Skips disabled locations. Slots that fall outside the day's open window are
    not generated. A slot is available iff no booking AND no applicable exclude
    overlaps it.
    """
    weekday = WEEKDAYS[_date.fromisoformat(iso_date).weekday()]
    day_hours = open_hours.get(weekday) or {}
    open_from = day_hours.get("from")
    open_to = day_hours.get("to")
    if not open_from or not open_to:
        return []

    window_start = _parse_hms(open_from)
    window_end = _parse_hms(open_to)
    base_slots = _slots_for_window(window_start, window_end)

    out: list[dict[str, Any]] = []
    for loc in locations:
        if not loc.get("isEnabled", True):
            continue

        loc_id = loc["id"]
        loc_bookings: list[tuple[int, int]] = []
        for b in bookings:
            if b.get("locationId") != loc_id:
                continue
            interval = _booking_minutes(b)
            if interval is not None:
                loc_bookings.append(interval)

        loc_excludes: list[tuple[int, int]] = []
        for e in excludes:
            if not _exclude_applies_to(e, loc_id):
                continue
            interval = _booking_minutes(e)
            if interval is not None:
                loc_excludes.append(interval)

        slots = []
        for s_start, s_end in base_slots:
            available = not any(
                _interval_overlap(s_start, s_end, b_start, b_end)
                for b_start, b_end in loc_bookings
            ) and not any(
                _interval_overlap(s_start, s_end, e_start, e_end)
                for e_start, e_end in loc_excludes
            )
            slots.append(
                {
                    "start": _fmt(s_start),
                    "end": _fmt(s_end),
                    "available": available,
                }
            )

        out.append(
            {
                "location_id": loc_id,
                "location_name": loc.get("name") or loc_id,
                "sport": derive_sport(loc.get("type", 0), loc.get("tags")),
                "slots": slots,
            }
        )

    out.sort(key=lambda r: (r["sport"] or "", r["location_name"]))
    return out
