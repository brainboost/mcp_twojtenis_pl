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

from .auth import session_manager
from .config import config
from .endpoints.clubs import clubs_endpoint
from .endpoints.reservations import reservations_endpoint
from .endpoints.schedules import schedule_endpoint

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
        logger.info(f"Retrieved {len(clubs)} clubs")
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
    logger.info(f"Retrieved {len(sports)} sports")
    return sports


@mcp.tool()
async def get_club_schedule(club_id: str, sport_id: int, date: str) -> dict[str, Any]:
    """Get court availability schedule for a specific club and sport.

    Args:
        club_id: Club identifier (e.g., 'blonia_sport')
        sport_id: Sport ID
        date: Date in DD.MM.YYYY format (e.g., '24.09.2025')

    Returns:
        Schedule data with court availability information
    """
    try:
        result = await schedule_endpoint.get_club_schedule(club_id, sport_id, date)
        return result

    except Exception as e:
        logger.error(f"Error getting club schedule: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "data": None,
        }


@mcp.tool()
async def get_reservations() -> list[dict[str, Any]]:
    """Get user's current court reservations.

    Returns:
        List of user's reservations
    """
    try:
        reservations = await reservations_endpoint.get_reservations()
        logger.info(f"Retrieved {len(reservations)} reservations")
        return reservations

    except Exception as e:
        logger.error(f"Error getting reservations: {e}")
        return []


@mcp.tool()
async def get_reservation_details(booking_id: str) -> dict[str, Any]:
    """Get reservation details for the booking_id.

    Returns:
        Reservation details
    """
    try:
        reservation = await reservations_endpoint.get_reservation_details(booking_id)
        logger.info(f"Retrieved reservation details for {booking_id}")
        return reservation

    except Exception as e:
        logger.error(f"Error getting reservation details for {booking_id}: {e}")
        return {}


@mcp.tool()
async def put_reservation(
    club_id: str,
    court_number: int,
    date: str,
    start_time: str,
    end_time: str,
    sport_id: int,
) -> dict[str, Any]:
    """Make a court reservation.

    Args:
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
            club_num=club.num,
            court_number=court_number,
            date=date,
            start_time=start_time,
            end_time=end_time,
            sport_id=sport_id,
        )

        if result["success"]:
            logger.info(
                f"Reservation made: {club_id}, court {court_number}, {date} from {start_time} to {end_time}"
            )
        else:
            logger.warning(f"Reservation failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Error making reservation: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


@mcp.tool()
async def delete_reservation(booking_id: str) -> dict[str, Any]:
    """Delete a court reservation.

    Args:
        booking_id: Reservation identifier (string)

    Returns:
        Deletion result with success status and message
    """
    try:
        result = await reservations_endpoint.delete_reservation(booking_id=booking_id)

        if result["success"]:
            logger.info(f"Reservation deleted: {booking_id}")
        else:
            logger.warning(f"Reservation deletion failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Error deleting reservation: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


@mcp.tool()
async def login(email: str, password: str) -> dict[str, Any]:
    """Initiate authentication with TwojTenis.pl

    Returns:
        Login result with success status:
        True if authentication succeeded, False otherwise
    """
    try:
        result = await reservations_endpoint.login(email=email, password=password)
        if result:
            return {
                "success": True,
                "message": "Authenticated",
            }
        return {"success": False, "message": "Authentication failed. Check credentials"}

    except Exception as e:
        logger.error(f"Login initiation failed: {e}")
        return {"success": False, "message": f"Login failed: {str(e)}"}


@mcp.tool()
async def get_session_status() -> dict[str, Any]:
    """Get current authentication session status.

    Returns:
        Current session status information
    """
    try:
        session = await session_manager.get_session()
        if session:
            return {
                "success": True,
                "authenticated": True,
                "session_id": session,
            }
        return {
            "success": True,
            "authenticated": False,
            "message": "No active session",
        }

    except Exception as e:
        logger.error(f"Session status check failed: {e}")
        return {
            "success": False,
            "authenticated": False,
            "message": f"Status check failed: {str(e)}",
        }


@mcp.tool()
async def logout() -> dict[str, Any]:
    """Logout and clear current session.

    Returns:
        Logout result
    """
    try:
        # Clear session
        await session_manager.logout()

        return {"success": True, "message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return {"success": False, "message": f"Logout failed: {str(e)}"}


async def initialize() -> None:
    """Initialize the server components."""

    # Initialize session manager
    logger.info("Initializing session manager...")
    await session_manager.initialize()

    # Get configuration info
    config_info = config.to_dict()
    logger.info(f"Configuration loaded: {config_info}")


def main() -> None:
    """Main server entry point."""
    # Initialize async components first
    asyncio.run(initialize())

    # Run the MCP server (synchronous)
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
