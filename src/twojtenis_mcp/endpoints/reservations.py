from typing import Any

from ..client import TwojTenisClient
from ..models import ApiErrorException, CourtBooking
from ..schedule_parser import ScheduleParser
from ..utils import validate_date, validate_time


class ReservationsEndpoint:
    """
    Endpoint for reservation related operations.
    Before calls to action methods, log in to setup auth session
    """

    def __init__(self):
        """Initialize reservations endpoint."""
        self.client = TwojTenisClient()

    async def login(self, email: str, password: str) -> str:
        """Login on the reservation site.

        Args:
            email: User email
            password: User password

        Returns:
            True if login successful, False otherwise
        """
        sess = await self.client.login(email=email, password=password)
        if sess is not None:
            return sess

        raise ApiErrorException(
            code="AUTH_ERROR",
            message="Authentication failed. Check your credentials for twojtenis.pl",
        )

    async def get_reservations(self, session_id: str) -> list[dict[str, Any]]:
        """Get user's current reservations.

        Args:
            session_id: Authenticated user's session ID

        Returns:
            List of reservation dictionaries
        """
        html_content = await self.client.with_session_retry(
            self.client.get_reservations, session_id=session_id
        )
        if not html_content:
            return []

        reservations = ScheduleParser.parse_reservations(html_content)
        result = []
        for reservation in reservations:  # type: ignore
            result.append(reservation)
        return result

    async def get_reservation_details(
        self, session_id: str, booking_id: str
    ) -> dict[str, Any]:
        """Get details of user's reservations.

        Args:
            session_id: Authenticated user's session ID
            booking_id: Reservation ID

        Returns:
            Reservation details dictionary
        """
        booking_info = {}
        try:
            booking_info = await self.client.with_session_retry(
                self.client.get_reservation,
                session_id=session_id,
                booking_id=booking_id,
            )

            if booking_info:
                reservation = ScheduleParser.parse_reservation(booking_info)
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
            return {
                "success": False,
                "message": f"Get details for reservation {booking_id} failed: {e.message}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error while getting reservation details: {str(e)}",
            }

    async def make_reservation(
        self,
        session_id: str,
        club_num: int,
        court_number: int,
        date: str,
        start_time: str,
        end_time: str,
        sport_id: int,
    ) -> dict[str, Any]:
        """Make a court reservation.

        Args:
            session_id: Authenticated user's session ID
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
            booking_id = await self.client.with_session_retry(
                self.client.make_reservation,
                session_id=session_id,
                club_num=club_num,
                sport_id=sport_id,
                court_number=court_number,
                date=date,
                start_time=start_time,
                end_time=end_time,
            )

            if booking_id:
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
            return {"success": False, "message": f"Reservation failed: {e.message}"}
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error while making reservation: {str(e)}",
            }

    async def make_bulk_reservation(
        self,
        session_id: str,
        club_num: int,
        sport_id: int,
        court_bookings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Make multiple court reservations in a single request.

        Args:
            session_id: Authenticated user's session ID
            club_num: Club number
            sport_id: Sport identifier
            court_bookings: List of booking dictionaries with keys:
                - court: Court number as string (e.g., "1", "2", "3")
                - date: Date in DD.MM.YYYY format (e.g., "27.12.2025")
                - time_start: Start time in HH:MM format (e.g., "21:00")
                - time_end: End time in HH:MM format (e.g., "21:30")

        Returns:
            Result dictionary with success status and message
        """
        if not court_bookings or len(court_bookings) == 0:
            return {
                "success": False,
                "message": "No bookings provided. At least one booking is required.",
            }

        # Validate all bookings
        for booking in court_bookings:
            date = booking.get("date", "")
            if not validate_date(date):
                return {
                    "success": False,
                    "message": "Invalid date format in booking. Use DD.MM.YYYY format.",
                }
            time_start = booking.get("time_start", "")
            time_end = booking.get("time_end", "")
            if not validate_time(time_start) or not validate_time(time_end):
                return {
                    "success": False,
                    "message": "Invalid time format in booking. Use HH:MM format.",
                }
            key = f"{date}_{time_start} - {time_end}"
            booking["key"] = key
        try:
            # Convert dicts to CourtBooking models
            booking_models = [CourtBooking(**b) for b in court_bookings]

            await self.client.with_session_retry(
                self.client.make_bulk_reservation,
                session_id=session_id,
                club_num=club_num,
                sport_id=sport_id,
                court_bookings=booking_models,
            )
            # get list of reservations
            reservations = await self.get_reservations(session_id=session_id)

            # correspond reservation ids with bookings
            booking_ids = {}
            if reservations and len(reservations) != 0:
                for booking in reservations:
                    booking_ids[f"{booking['date']}_{booking['time']}"] = booking[
                        "booking_id"
                    ]

                # Track successful and failed bookings
                successful_count = 0

                for court_booking in court_bookings:
                    key = court_booking["key"]
                    found_id = booking_ids.get(key)
                    if found_id:
                        court_booking["booking_id"] = found_id
                        court_booking["success"] = True
                        successful_count += 1
                    else:
                        court_booking["success"] = False
                    del court_booking["key"]

                # Determine overall success - at least one booking succeeded
                overall_success = successful_count > 0

                # Build appropriate message
                if successful_count == len(court_bookings):
                    message = f"Bulk reservation made for {successful_count} court(s)"
                else:
                    failed_count = len(court_bookings) - successful_count
                    message = (
                        f"Partial bulk reservation: {successful_count} court(s) booked, "
                        f"{failed_count} court(s) unavailable"
                    )

                return {
                    "success": overall_success,
                    "message": message,
                    "reservation": {
                        "club_num": club_num,
                        "count": len(court_bookings),
                        "bookings": court_bookings,
                        "sport_id": sport_id,
                    },
                }
            else:
                # No reservations found - all bookings failed, don't return reservation details
                return {
                    "success": False,
                    "message": f"Failed to make bulk reservation. All {len(court_bookings)} court(s) are unavailable.",
                }

        except ApiErrorException as e:
            return {
                "success": False,
                "message": f"Bulk reservation failed: {e.message}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error while making bulk reservation: {str(e)}",
            }

    async def delete_reservation(
        self, session_id: str, booking_id: str
    ) -> dict[str, Any]:
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
                session_id=session_id,
                booking_id=booking_id,
            )
            if success:
                msg = f"Reservation deleted successfully: {booking_id}"
                return {
                    "success": True,
                    "message": msg,
                }
            else:
                msg = f"Failed to delete reservation {booking_id}. The reservation might not exist."
                return {
                    "success": False,
                    "message": msg,
                }
        except ApiErrorException as e:
            return {
                "success": False,
                "message": f"Reservation {booking_id} deletion failed: {e.message}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Reservation {booking_id} deletion failed. Unexpected error: {str(e)}",
            }

    async def delete_all_reservations(self, session_id: str) -> dict[str, Any]:
        """Delete all of the user's current reservations.

        Args:
            session_id: Authenticated user's session ID

        Returns:
            Result dictionary with success status, message, and list of deleted booking IDs
        """
        try:
            # Get all user reservations
            reservations = await self.get_reservations(session_id=session_id)

            if not reservations:
                return {
                    "success": True,
                    "message": "No reservations found to delete",
                    "deleted_count": 0,
                    "deleted_booking_ids": [],
                }

            # Delete each reservation
            deleted_booking_ids = []
            failed_deletions = []

            for reservation in reservations:
                booking_id = reservation.get("booking_id")
                if booking_id:
                    result = await self.client.with_session_retry(
                        self.client.delete_reservation,
                        session_id=session_id,
                        booking_id=booking_id,
                    )
                    if result:
                        deleted_booking_ids.append(booking_id)
                    else:
                        failed_deletions.append(booking_id)

            # Prepare result message
            total_count = len(reservations)
            success_count = len(deleted_booking_ids)
            failed_count = len(failed_deletions)

            if failed_count == 0:
                message = f"Successfully deleted all {success_count} reservation(s)"
            elif success_count == 0:
                message = f"Failed to delete any of the {total_count} reservation(s)"
            else:
                message = (
                    f"Deleted {success_count} of {total_count} reservation(s). "
                    f"{failed_count} deletion(s) failed: {failed_deletions}"
                )

            return {
                "success": failed_count == 0,
                "message": message,
                "deleted_count": success_count,
                "deleted_booking_ids": deleted_booking_ids,
                "failed_booking_ids": failed_deletions,
            }

        except ApiErrorException as e:
            return {
                "success": False,
                "message": f"Delete all reservations failed: {e.message}",
                "deleted_count": 0,
                "deleted_booking_ids": [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Delete all reservations failed. Unexpected error: {str(e)}",
                "deleted_count": 0,
                "deleted_booking_ids": [],
            }


# Global reservations endpoint instance
reservations_endpoint = ReservationsEndpoint()
