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
from .endpoints.booking import booking_endpoint
from .endpoints.clubs import clubs_endpoint
from .endpoints.reservations import reservations_endpoint
from .models import SportId

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("TwojTenis Court Booking Server")


@mcp.tool()
async def get_clubs() -> list[dict[str, Any]]:
    """Get list of available tennis and badminton clubs.

    Returns:
        List of clubs with their details
    """
    try:
        clubs = clubs_endpoint.get_clubs()
        logger.info(f"Retrieved {len(clubs)} clubs")
        return clubs

    except Exception as e:
        logger.error(f"Error getting clubs: {e}")
        return []


@mcp.tool()
async def get_sports() -> dict[str, Any]:
    """Get list of supported sports.

    Returns:
        List of sports with their IDs and names
    """
    sports = {str(sport): sport.value for sport in SportId}
    logger.info(f"Retrieved {len(sports)} sports")
    return sports


@mcp.tool()
async def get_club_schedule(club_id: str, sport_id: int, date: str) -> dict[str, Any]:
    """Get court availability schedule for a specific club and sport.

    Args:
        club_id: Club identifier (e.g., 'blonia_sport')
        sport_id: Sport ID (84 for badminton, 70 for tennis)
        date: Date in DD.MM.YYYY format (e.g., '24.09.2025')

    Returns:
        Schedule data with court availability information
    """
    try:
        result = await booking_endpoint.get_club_schedule(club_id, sport_id, date)
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
async def put_reservation(
    club_id: str, court_number: int, date: str, hour: str, sport_id: int
) -> dict[str, Any]:
    """Make a court reservation.

    Args:
        club_id: Club identifier (e.g., 'blonia_sport')
        court_number: Court number (e.g., 1, 2, 3...)
        date: Date in DD.MM.YYYY format (e.g., '24.09.2025')
        hour: Time in HH:MM format (e.g., '10:00', '10:30')
        sport_id: Sport ID (84 for badminton, 70 for tennis)

    Returns:
        Reservation result with success status and details
    """
    try:
        result = await reservations_endpoint.make_reservation(
            club_id=club_id,
            court_number=court_number,
            date=date,
            hour=hour,
            sport_id=sport_id,
        )

        if result["success"]:
            logger.info(
                f"Reservation made: {club_id}, court {court_number}, {date} {hour}"
            )
        else:
            logger.warning(f"Reservation failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Error making reservation: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


@mcp.tool()
async def delete_reservation(
    club_id: str, court_number: int, date: str, hour: str
) -> dict[str, Any]:
    """Delete a court reservation.

    Args:
        club_id: Club identifier (e.g., 'blonia_sport')
        court_number: Court number (e.g., 1, 2, 3...)
        date: Date in DD.MM.YYYY format (e.g., '24.09.2025')
        hour: Time in HH:MM format (e.g., '10:00', '10:30')

    Returns:
        Deletion result with success status and message
    """
    try:
        result = await reservations_endpoint.delete_reservation(
            club_id=club_id, court_number=court_number, date=date, hour=hour
        )

        if result["success"]:
            logger.info(
                f"Reservation deleted: {club_id}, court {court_number}, {date} {hour}"
            )
        else:
            logger.warning(f"Reservation deletion failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"Error deleting reservation: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


async def initialize() -> None:
    """Initialize the server components."""
    logger.info("Starting TwojTenis MCP Server...")

    # Initialize session manager
    logger.info("Initializing session manager...")
    await session_manager.initialize()

    # Get configuration info
    config_info = config.to_dict()
    logger.info(f"Configuration loaded: {config_info}")
    logger.info("TwojTenis MCP Server is ready to accept connections.")


def main() -> None:
    """Main server entry point."""
    # Initialize async components first
    asyncio.run(initialize())

    # Run the MCP server (synchronous)
    mcp.run()


if __name__ == "__main__":
    main()
