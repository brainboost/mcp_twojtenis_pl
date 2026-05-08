from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastmcp import FastMCP

from .client import ApiClient
from .config import config
from .endpoints.clubs import ClubsEndpoint
from .endpoints.oauth import oauth_endpoint
from .endpoints.reservations import ReservationsEndpoint
from .endpoints.schedules import SchedulesEndpoint
from .locations import LocationsService
from .models import ApiErrorException
from .tech_group import TechGroupResolver
from .utils import to_iso_date

mcp = FastMCP("twojtenis-mcp")

_client = ApiClient(main_base=config.main_api_url, timeout=config.request_timeout)
_resolver = TechGroupResolver(_client)
_clubs = ClubsEndpoint(_client)
_schedules = SchedulesEndpoint(_client, _resolver)
_reservations = ReservationsEndpoint(_client, _resolver)
_locations = LocationsService(_client)


def _err(exc: ApiErrorException) -> dict[str, Any]:
    return {
        "success": False,
        "message": exc.message,
        "code": exc.code,
        "details": exc.details,
    }


@mcp.tool()
async def get_all_clubs(access_token: str) -> Any:
    """List all clubs available on TwojTenis."""
    try:
        return await _clubs.list_clubs(access_token=access_token)
    except ApiErrorException as exc:
        return _err(exc)


@mcp.tool()
async def get_club_locations(
    access_token: str, club_id: str, sport: str = ""
) -> Any:
    """List the bookable courts (locations) at one club.

    Each entry has `id` (use as `location_id` in put_reservation), `name`
    (use as `location_name`), `sport` (derived: "tennis", "badminton",
    "padel", "squash", "table_tennis", "fitness", "bowling", "football",
    "multi", or None if unknown), plus `short_name`, `tags`, `sort_number`,
    `type`, `has_light`, `is_enabled`, `group_name`.

    Pass `sport` to filter (case-insensitive). E.g. sport="badminton".
    """
    try:
        locs = await _locations.locations_for_club(
            club_id, access_token=access_token, sport=sport or None
        )
        return [loc.model_dump(by_alias=False) for loc in locs]
    except ApiErrorException as exc:
        return _err(exc)


@mcp.tool()
async def get_club_schedule(
    access_token: str, club_id: str, date: str
) -> dict[str, Any]:
    """Public schedule (occupied slots + excludes) for one club on one day."""
    try:
        return await _schedules.get_club_schedule(
            club_id=club_id, date=date, access_token=access_token
        )
    except ApiErrorException as exc:
        return _err(exc)


@mcp.tool()
async def get_reservations(
    access_token: str, from_date: str = "", to_date: str = ""
) -> Any:
    """List the user's bookings between from_date and to_date.

    Date format: DD.MM.YYYY or YYYY-MM-DD. Defaults: today .. today+90 days.
    """
    today = date.today()
    try:
        from_iso = to_iso_date(from_date) if from_date else today.isoformat()
        to_iso = (
            to_iso_date(to_date)
            if to_date
            else (today + timedelta(days=90)).isoformat()
        )
        return await _reservations.get_reservations(
            access_token=access_token, from_iso=from_iso, to_iso=to_iso
        )
    except ApiErrorException as exc:
        return _err(exc)
    except ValueError as exc:
        return _err(ApiErrorException("VALIDATION_ERROR", str(exc)))


@mcp.tool()
async def get_reservation_details(access_token: str, booking_id: str) -> dict[str, Any]:
    """Look up a single booking by ID (searches today-30d .. today+90d)."""
    try:
        out = await _reservations.get_reservation_details(
            booking_id=booking_id, access_token=access_token
        )
        if out is None:
            return {"success": False, "message": "booking not found"}
        return {"success": True, "reservation": out}
    except ApiErrorException as exc:
        return _err(exc)


@mcp.tool()
async def put_reservation(
    access_token: str,
    club_id: str,
    location_id: str,
    location_name: str,
    date: str,
    start_time: str,
    end_time: str,
) -> dict[str, Any]:
    """Create one reservation for the given court (location) and time."""
    try:
        return await _reservations.make_reservation(
            club_id=club_id,
            location_id=location_id,
            location_name=location_name,
            date=date,
            start_time=start_time,
            end_time=end_time,
            access_token=access_token,
        )
    except ApiErrorException as exc:
        return _err(exc)


@mcp.tool()
async def put_bulk_reservation(
    access_token: str, club_id: str, court_bookings: list[dict[str, Any]]
) -> dict[str, Any]:
    """Create multiple reservations in one server-side call.

    Each item in court_bookings:
      {location_id, location_name, date, start_time, end_time}
    """
    try:
        return await _reservations.make_bulk_reservation(
            club_id=club_id,
            court_bookings=court_bookings,
            access_token=access_token,
        )
    except ApiErrorException as exc:
        return _err(exc)


@mcp.tool()
async def delete_reservation(access_token: str, booking_id: str) -> dict[str, Any]:
    """Cancel a single reservation by ID."""
    try:
        return await _reservations.delete_reservation(
            booking_id=booking_id, access_token=access_token
        )
    except ApiErrorException as exc:
        return _err(exc)


@mcp.tool()
async def delete_all_reservations(access_token: str) -> dict[str, Any]:
    """Cancel every future reservation owned by the authenticated user."""
    try:
        return await _reservations.delete_all_reservations(access_token=access_token)
    except ApiErrorException as exc:
        return _err(exc)


@mcp.tool()
async def login_oauth(email: str, password: str) -> dict[str, Any]:
    """Drive an Auth0 headless-browser login and return a JWT access_token."""
    try:
        result = await oauth_endpoint.login(email, password)
        return {"success": True, **result}
    except ApiErrorException as exc:
        return _err(exc)


@mcp.tool()
async def refresh_oauth_token(refresh_token: str) -> dict[str, Any]:
    """Exchange a refresh_token for a new access_token (no browser)."""
    try:
        result = await oauth_endpoint.refresh(refresh_token)
        return {"success": True, **result}
    except ApiErrorException as exc:
        return _err(exc)


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug:
        try:
            import debugpy

            debugpy.listen(("localhost", 5678))
            debugpy.wait_for_client()
        except ImportError:
            print("debugpy not installed", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
