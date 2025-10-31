"""Booking and schedule-related MCP endpoints."""

import logging
from typing import Any

from ..auth import session_manager
from ..client import TwojTenisClient, with_session_retry
from ..models import ApiErrorException, Court, Schedule, SportId
from ..schedule_parser import ScheduleParser

logger = logging.getLogger(__name__)


class BookingEndpoint:
    """Endpoint for booking and schedule operations."""

    def __init__(self):
        """Initialize booking endpoint."""
        self.client = TwojTenisClient()

    async def get_club_schedule(
        self, club_id: str, sport_id: int, date: str
    ) -> dict[str, Any]:
        """Get club schedule for specific date and sport.

        Args:
            club_id: Club identifier
            sport_id: Sport identifier (84=badminton, 70=tennis)
            date: Date in DD.MM.YYYY format

        Returns:
            Schedule data dictionary
        """
        try:
            # Validate inputs
            if not self._validate_date(date):
                return {
                    "success": False,
                    "message": "Invalid date format. Use DD.MM.YYYY format.",
                    "data": None,
                }

            if sport_id not in SportId:
                return {
                    "success": False,
                    "message": "Invalid sport ID",
                    "data": None,
                }

            # Get schedule data with retry logic
            schedule_data = await with_session_retry(
                self.client.get_club_schedule,
                session_manager,
                club_url=club_id,
                sport_id=sport_id,
                date=date,
            )

            if not schedule_data:
                return {
                    "success": False,
                    "message": "Failed to retrieve schedule data.",
                    "data": None,
                }

            # Parse schedule
            schedules = ScheduleParser.parse_schedules(
                json_str=schedule_data,
            )
            if not schedules:
                return {
                    "success": True,
                    "message": "Empty schedule data.",
                    "data": None,
                }
            courts = []
            for sched in schedules:
                if int(sched["sport"]) == int(sport_id):
                    courts_data = sched["data"]
                    for c in courts_data:
                        courts.append(
                            Court(number=c["number"], availability=c["availability"])
                        )
                    schedule = Schedule(
                        club_id=club_id,
                        sport_id=SportId(sport_id),
                        date=date,
                        courts=courts,
                    )
                    logger.info(
                        f"Retrieved schedule for {club_id}, sport {sport_id} on {date}"
                    )
                    return {
                        "success": True,
                        "message": "Schedule retrieved successfully",
                        "data": schedule.model_dump(),
                    }
            return {
                "success": True,
                "message": "No schedules for the selected sport found. Try use different parameters",
                "data": None,
            }

        except ApiErrorException as e:
            logger.error(f"API error getting schedule: {e.message}")
            return {
                "success": False,
                "message": f"Failed to get schedule: {e.message}",
                "data": None,
            }
        except Exception as e:
            logger.error(f"Unexpected error getting schedule: {e}")
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "data": None,
            }

    def _validate_date(self, date: str) -> bool:
        """Validate date format (DD.MM.YYYY).

        Args:
            date: Date string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            import re

            if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date):
                return False

            day, month, year = map(int, date.split("."))

            # Basic validation
            if not (1 <= day <= 31):
                return False
            if not (1 <= month <= 12):
                return False
            if not (2020 <= year <= 2030):  # Reasonable year range
                return False

            return True

        except (ValueError, AttributeError):
            return False


# Global booking endpoint instance
booking_endpoint = BookingEndpoint()
