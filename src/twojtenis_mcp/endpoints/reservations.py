"""Reservation-related MCP endpoints."""

import logging
from typing import Any

from ..auth import session_manager
from ..client import TwojTenisClient, with_session_retry
from ..models import ApiErrorException
from ..schedule_parser import ScheduleParser

logger = logging.getLogger(__name__)


class ReservationsEndpoint:
    """Endpoint for reservation-related operations."""

    def __init__(self):
        """Initialize reservations endpoint."""
        self.client = TwojTenisClient()

    async def get_reservations(self) -> list[dict[str, Any]]:
        """Get user's current reservations.

        Returns:
            List of reservation dictionaries
        """
        try:
            html_content = await with_session_retry(
                self.client.get_reservations,
                session_manager,
            )
            if not html_content:
                logger.warning("No reservation data received")
                return []

            # Parse reservations from HTML
            reservations = ScheduleParser.parse_reservations(html_content)

            # Convert to dictionaries and add user_id
            result = []
            for reservation in reservations:
                reservation["user_id"] = (await session_manager.get_session()).phpsessid
                result.append(reservation)

            logger.info(f"Retrieved {len(result)} reservations")
            return result

        except ApiErrorException as e:
            logger.error(f"Failed to get reservations: {e.message}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting reservations: {e}")
            return []

    async def make_reservation(
        self, club_id: str, court_number: int, date: str, hour: str, sport_id: int
    ) -> dict[str, Any]:
        """Make a court reservation.

        Args:
            club_id: Club identifier
            court_number: Court number
            date: Date in DD.MM.YYYY format
            hour: Hour in HH:MM format
            sport_id: Sport identifier

        Returns:
            Result dictionary with success status and message
        """
        try:
            # Validate date format
            if not self._validate_date(date):
                return {
                    "success": False,
                    "message": "Invalid date format. Use DD.MM.YYYY format.",
                }

            # Validate time format
            if not self._validate_time(hour):
                return {
                    "success": False,
                    "message": "Invalid time format. Use HH:MM format.",
                }

            # Make reservation with retry logic
            success = await with_session_retry(
                self.client.make_reservation,
                session_manager,
                club_id=club_id,
                sport_id=sport_id,
                court_number=court_number,
                date=date,
                hour=hour,
            )

            if success:
                logger.info(
                    f"Reservation made successfully: {club_id}, court {court_number}, {date} {hour}"
                )
                session = await session_manager.get_session()
                return {
                    "success": True,
                    "message": f"Reservation made for court {court_number} on {date} at {hour}",
                    "reservation": {
                        "user_id": session.phpsessid if session else "unknown",
                        "club_id": club_id,
                        "court_number": court_number,
                        "date": date,
                        "hour": hour,
                        "sport_id": sport_id,
                    },
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to make reservation. The court might be unavailable.",
                }

        except ApiErrorException as e:
            logger.error(f"API error making reservation: {e.message}")
            return {"success": False, "message": f"Reservation failed: {e.message}"}
        except Exception as e:
            logger.error(f"Unexpected error making reservation: {e}")
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

    async def delete_reservation(
        self, club_id: str, court_number: int, date: str, hour: str
    ) -> dict[str, Any]:
        """Delete a court reservation.

        Args:
            club_id: Club identifier
            court_number: Court number
            date: Date in DD.MM.YYYY format
            hour: Hour in HH:MM format

        Returns:
            Result dictionary with success status and message
        """
        try:
            # Validate date format
            if not self._validate_date(date):
                return {
                    "success": False,
                    "message": "Invalid date format. Use DD.MM.YYYY format.",
                }

            # Validate time format
            if not self._validate_time(hour):
                return {
                    "success": False,
                    "message": "Invalid time format. Use HH:MM format.",
                }

            # For deletion, we need to determine the sport_id
            # This is a limitation - we might need to query the reservation first
            # For now, we'll try both sports or use a default
            sport_ids = [84, 70]  # badminton, tennis

            success = False
            last_exception = None
            
            for sport_id in sport_ids:
                try:
                    success = await with_session_retry(
                        self.client.delete_reservation,
                        session_manager,
                        club_id=club_id,
                        sport_id=sport_id,
                        court_number=court_number,
                        date=date,
                        hour=hour,
                    )
                    if success:
                        break
                except ApiErrorException as e:
                    last_exception = e
                    continue

            if success:
                logger.info(
                    f"Reservation deleted successfully: {club_id}, court {court_number}, {date} {hour}"
                )
                return {
                    "success": True,
                    "message": f"Reservation deleted for court {court_number} on {date} at {hour}",
                }
            else:
                error_msg = "Failed to delete reservation. The reservation might not exist."
                if last_exception:
                    error_msg = f"Deletion failed: {last_exception.message}"
                return {
                    "success": False,
                    "message": error_msg,
                }

        except ApiErrorException as e:
            logger.error(f"API error deleting reservation: {e.message}")
            return {"success": False, "message": f"Deletion failed: {e.message}"}
        except Exception as e:
            logger.error(f"Unexpected error deleting reservation: {e}")
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

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

    def _validate_time(self, time: str) -> bool:
        """Validate time format (HH:MM).

        Args:
            time: Time string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            import re

            if not re.match(r"^\d{2}:\d{2}$", time):
                return False

            hour, minute = map(int, time.split(":"))

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


# Global reservations endpoint instance
reservations_endpoint = ReservationsEndpoint()
