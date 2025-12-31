"""Main MCP server implementation for TwojTenis.pl."""

import asyncio
import logging
import sys
from typing import Any

if "--debug" in sys.argv:
    import debugpy

    debugpy.listen(("127.0.0.1", 5678))
    print(
        "⏳ Waiting for debugger to attach on port 5678...", file=sys.stderr, flush=True
    )
    debugpy.wait_for_client()
    print("✅ Debugger attached!", file=sys.stderr, flush=True)

from fastmcp import FastMCP

# from .auth import session_manager
from .config import config
from .endpoints.clubs import clubs_endpoint
from .endpoints.reservations import reservations_endpoint
from .endpoints.schedules import schedule_endpoint

# Configure logging
logging.basicConfig(
    filename="twojtenis_mcp.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("TwojTenis Court Booking Server")


@mcp.tool()
async def get_all_clubs() -> list[dict[str, Any]]:
    """Get list of available tennis and badminton clubs.

    Returns:
        List of clubs with their details
    """
    try:
        clubs = await clubs_endpoint.get_clubs()
        logger.debug(f"Retrieved {len(clubs)} clubs")
        return clubs

    except Exception as e:
        logger.error(f"Error getting clubs: {e}")
        return []


@mcp.tool()
async def get_all_sports() -> dict[int, str]:
    """Get list of all supported sports.

    Returns:
        List of sports with their IDs and names
    """
    sports: dict[int, str] = {}
    for sport in clubs_endpoint.get_sports():
        sports[sport["id"]] = sport["name"]
    logger.debug(f"Retrieved {len(sports)} sports")
    return sports


@mcp.tool()
async def get_club_schedule(
    session_id: str, club_id: str, sport_id: int, date: str
) -> dict[str, Any]:
    """Get court availability schedule for the specific club and sport.

    Args:
        session_id: Logged user session ID (call login to retrieve)
        club_id: Club identifier (e.g., 'blonia_sport')
        sport_id: Sport ID
        date: Date in DD.MM.YYYY format (e.g., '24.09.2025')

    Returns:
        Schedule data with court availability information
    """
    try:
        result = await schedule_endpoint.get_club_schedule(
            session_id, club_id, sport_id, date
        )
        logger.debug(
            f"Retrieved {len(result)} results for club {club_id}, sport {sport_id}"
        )
        return result

    except Exception as e:
        logger.error(
            f"Error getting club {club_id} schedule for sport {sport_id}, session_id {session_id}: {e}"
        )
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "data": None,
        }


@mcp.tool()
async def get_reservations(session_id: str) -> list[dict[str, Any]]:
    """Get user's current court reservations.

    Args:
        session_id: Logged user session ID (call login to retrieve)

    Returns:
        List of user's reservations
    """
    try:
        reservations = await reservations_endpoint.get_reservations(session_id)
        logger.debug(f"Retrieved {len(reservations)} reservations")
        return reservations

    except Exception as e:
        logger.error(f"Error getting reservations: {e}")
        return []


@mcp.tool()
async def get_reservation_details(session_id: str, booking_id: str) -> dict[str, Any]:
    """Get reservation details.

    Args:
        session_id: Logged user session ID (call login to retrieve)
        booking_id: Reservation ID

    Returns:
        Reservation details
    """
    try:
        reservation = await reservations_endpoint.get_reservation_details(
            session_id, booking_id
        )
        logger.debug(
            f"Retrieved reservation details for {session_id}, booking_id: {booking_id}"
        )
        return reservation

    except Exception as e:
        logger.error(
            f"Error getting reservation details for {session_id}, booking_id: {booking_id}: {e}"
        )
        return {}


@mcp.tool()
async def put_reservation(
    session_id: str,
    club_id: str,
    court_number: int,
    date: str,
    start_time: str,
    end_time: str,
    sport_id: int,
) -> dict[str, Any]:
    """Make a court reservation.

    Args:
        session_id: Logged user session ID (call login to retrieve)
        club_id: Club identifier (e.g., 'blonia_sport')
        court_number: Court number starting from 1 (e.g., 1, 2, 3...)
        date: Date in DD.MM.YYYY format (e.g., '24.09.2025')
        start_time: Start time in HH:MM format (e.g., '10:00')
        end_time: End time in HH:MM format (e.g., '11:00')
        sport_id: Sport ID (84 for badminton, 70 for tennis)

    Returns:
        Reservation result with success status and details
    """
    try:
        club = await clubs_endpoint.get_club_by_id(club_id)
        if not club:
            return {"success": False, "message": f"Error: unknown club {club_id}"}

        result = await reservations_endpoint.make_reservation(
            session_id=session_id,
            club_num=club.num,
            court_number=court_number,
            date=date,
            start_time=start_time,
            end_time=end_time,
            sport_id=sport_id,
        )

        if result["success"]:
            logger.debug(
                f"Reservation made for {session_id}, club: {club_id}, court: {court_number}, {date} from {start_time} to {end_time}"
            )
        else:
            logger.warning(f"Reservation failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(
            f"Error making reservation for {session_id}, club: {club_id}, sport {sport_id}, on date {date}: {e}"
        )
        return {"success": False, "message": f"Error: {str(e)}"}


@mcp.tool()
async def delete_reservation(session_id: str, booking_id: str) -> dict[str, Any]:
    """Delete a court reservation.

    Args:
        session_id: Logged user session ID
        booking_id: Reservation identifier (string)

    Returns:
        Deletion result with success status and message
    """
    try:
        result = await reservations_endpoint.delete_reservation(
            session_id=session_id, booking_id=booking_id
        )

        if result["success"]:
            logger.debug(f"Reservation deleted: {booking_id}")
        else:
            logger.warning(f"Reservation deletion failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Error deleting reservation: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


@mcp.tool()
async def delete_all_reservations(session_id: str) -> dict[str, Any]:
    """Delete all of the user's current court reservations.

    Args:
        session_id: Logged user session ID (call login to retrieve)

    Returns:
        Deletion result with success status, message, deleted count, and lists of deleted/failed booking IDs
    """
    try:
        result = await reservations_endpoint.delete_all_reservations(
            session_id=session_id
        )

        if result["success"]:
            logger.debug(
                f"Deleted {result['deleted_count']} reservation(s): {result.get('deleted_booking_ids', [])}"
            )
        else:
            logger.warning(f"Delete all reservations failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Error deleting all reservations: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


@mcp.tool()
async def put_bulk_reservation(
    session_id: str,
    club_id: str,
    sport_id: int,
    court_bookings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Make multiple court reservations in a single request.

    Args:
        session_id: Logged user session ID (call login to retrieve)
        club_id: Club identifier (e.g., 'blonia_sport')
        sport_id: Sport ID (84 for badminton, 70 for tennis)
        court_bookings: List of booking dictionaries, each containing:
            - court: Court number as string (e.g., "1", "2", "3")
            - date: Date in DD.MM.YYYY format (e.g., "27.12.2025")
            - time_start: Start time in HH:MM format (e.g., "21:00")
            - time_end: End time in HH:MM format (e.g., "21:30")

    Returns:
        Reservation result with success status and details

    Example:
        court_bookings = [
            {"court": "1", "date": "27.12.2025", "time_start": "21:00", "time_end": "21:30"},
            {"court": "2", "date": "27.12.2025", "time_start": "21:00", "time_end": "21:30"}
        ]
    """
    try:
        club = await clubs_endpoint.get_club_by_id(club_id)
        if not club:
            return {"success": False, "message": f"Error: unknown club {club_id}"}

        result = await reservations_endpoint.make_bulk_reservation(
            session_id=session_id,
            club_num=club.num,
            sport_id=sport_id,
            court_bookings=court_bookings,
        )

        if result["success"]:
            logger.debug(
                f"Bulk reservation for {session_id}, club: {club_id}, {len(court_bookings)} bookings"
            )
        else:
            logger.warning(f"Bulk reservation failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(
            f"Error making bulk reservation for {session_id}, club: {club_id}, sport {sport_id}: {e}"
        )
        return {"success": False, "message": f"Error: {str(e)}"}


@mcp.tool()
async def login(email: str, password: str) -> dict[str, Any]:
    """Initiate authentication with TwojTenis.pl

    Returns:
        Login result with success status:
        session_id: Authenticated user's session ID
    """
    try:
        result = await reservations_endpoint.login(email=email, password=password)
        if result:
            logger.debug(f"Authentication succeeded for {email}. Session_id {result}")
            return {"success": True, "message": "Authenticated", "session_id": result}
        logger.error(f"Authentication failed for {email}")
        return {"success": False, "message": "Authentication failed. Check credentials"}

    except Exception as e:
        logger.error(f"Login initiation failed: {e}")
        return {"success": False, "message": f"Login failed: {str(e)}"}


async def initialize() -> None:
    """Initialize the server components."""

    # Get configuration info
    config_info = config.to_dict()
    logger.debug(f"Configuration loaded: {config_info}")


def main() -> None:
    """Main server entry point."""
    # Initialize async components first
    asyncio.run(initialize())

    # Run the MCP server (synchronous)
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
