"""Reservation-related MCP endpoints."""

import logging
from typing import Any

from ..client import TwojTenisClient
from ..models import ApiErrorException
from ..schedule_parser import ScheduleParser
from ..utils import validate_date, validate_time

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
            html_content = await self.client.with_session_retry(
                self.client.get_reservations,
            )
            if not html_content:
                logger.warning("No reservation data received")
                return []

            reservations = ScheduleParser.parse_reservations(html_content)
            result = []
            for reservation in reservations:  # type: ignore
                result.append(reservation)

            logger.info(f"Retrieved {len(result)} reservations")
            return result

        except ApiErrorException as e:
            logger.error(f"Failed to get reservations: {e.message}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting reservations: {e}")
            return []

    async def get_reservation_details(self, booking_id: str) -> dict[str, Any]:
        booking_info = {}
        try:
            # with retry logic
            booking_info = await self.client.with_session_retry(
                self.client.get_reservation,
                booking_id=booking_id,
            )

            if booking_info:
                reservation = ScheduleParser.parse_reservation(booking_info)
                logger.info(f"Get details for reservation {booking_id} succeeded")
                if reservation:
                    return {
                        "success": True,
                        "message": f"Getting details for reservation {booking_id}",
                        "reservation": {
                            "booking_id": booking_id,
                            "club_id": reservation["club_id"],
                            "club_name": reservation["club_name"],
                            "club_num": reservation["club_num"],
                            "sport": reservation["sport"],
                            "court": reservation["court"],
                            "details": reservation["details"],
                            "date": reservation["date"],
                            "time": reservation["time"],
                            "cancel_till": reservation["cancel_till"],
                            "price": reservation["price"],
                            "pay_till": reservation["pay_till"],
                        },
                    }

            return {
                "success": False,
                "message": f"Failed to get reservation {booking_id} details.",
            }

        except ApiErrorException as e:
            logger.error(f"API error making reservation: {e.message}")
            return {
                "success": False,
                "message": f"Get details for reservation {booking_id} failed: {e.message}",
            }
        except Exception as e:
            logger.error(f"Unexpected error getting reservation details: {e}")
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

    async def make_reservation(
        self,
        club_num: int,
        court_number: int,
        date: str,
        start_time: str,
        end_time: str,
        sport_id: int,
    ) -> dict[str, Any]:
        """Make a court reservation.

        Args:
            club_num: Club number
            court_number: Court number, from 1
            date: Date in DD.MM.YYYY format
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            sport_id: Sport identifier

        Returns:
            Result dictionary with success status and message
        """
        if not validate_date(date):
            return {
                "success": False,
                "message": "Invalid date format. Use DD.MM.YYYY format.",
            }

        if not validate_time(start_time) or not validate_time(end_time):
            return {
                "success": False,
                "message": "Invalid time format. Use HH:MM format.",
            }

        try:
            # with retry logic
            booking_id = await self.client.with_session_retry(
                self.client.make_reservation,
                club_num=club_num,
                sport_id=sport_id,
                court_number=court_number,
                date=date,
                start_time=start_time,
                end_time=end_time,
            )

            if booking_id:
                logger.info(
                    f"Reservation {booking_id} made successfully: #{club_num}, court {court_number}, {date} from {start_time} to {end_time}"
                )
                # session = await session_manager.get_session()
                return {
                    "success": True,
                    "message": f"Reservation made for court {court_number} on {date} from {start_time} to {end_time}",
                    "reservation": {
                        "booking_id": booking_id,
                        "club_num": club_num,
                        "court_number": court_number,
                        "date": date,
                        "start_time": start_time,
                        "end_time": end_time,
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

    async def delete_reservation(self, booking_id: str) -> dict[str, Any]:
        """Delete a court reservation.

        Args:
            booking_id: Reservation identifier

        Returns:
            Result dictionary with success status and message
        """
        success = False

        try:
            success = await self.client.with_session_retry(
                self.client.delete_reservation,
                booking_id=booking_id,
            )
            if success:
                msg = f"Reservation deleted successfully: {booking_id}"
                logger.info(msg=msg)
                return {
                    "success": True,
                    "message": msg,
                }
            else:
                msg = f"Failed to delete reservation {booking_id}. The reservation might not exist."
                logger.error(msg=msg)
                return {
                    "success": False,
                    "message": msg,
                }
        except ApiErrorException as e:
            logger.error(f"API error deleting reservation: {e.message}")
            return {
                "success": False,
                "message": f"Reservation {booking_id} deletion failed: {e.message}",
            }
        except Exception as e:
            logger.error(f"Unexpected error deleting reservation: {e}")
            return {
                "success": False,
                "message": f"Reservation {booking_id} deletion failed. Unexpected error: {str(e)}",
            }


# Global reservations endpoint instance
reservations_endpoint = ReservationsEndpoint()
