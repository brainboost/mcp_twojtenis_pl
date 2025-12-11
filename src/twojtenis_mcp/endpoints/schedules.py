import json
from typing import Any

from ..client import TwojTenisClient
from ..models import ApiErrorException, Court, Schedule
from ..schedule_parser import ScheduleParser
from ..utils import validate_date


class ScheduleEndpoint:
    """Endpoint for reading club schedules."""

    def __init__(self):
        """Initialize endpoint."""
        self.client = TwojTenisClient()

    async def get_club_schedule(
        self, session_id: str, club_id: str, sport_id: int, date: str
    ) -> dict[str, Any]:
        """Get club schedule for specific date and sport.

        Args:
            session_id: Logged user session ID
            club_id: Club identifier
            sport_id: Sport identifier
            date: Date in DD.MM.YYYY format

        Returns:
            Schedule data dictionary
        """
        # Validate inputs
        if not validate_date(date):
            return {
                "success": False,
                "message": "Invalid date format. Use DD.MM.YYYY format.",
                "data": None,
            }

        if sport_id <= 0:
            return {
                "success": False,
                "message": "Invalid sport_id. Use get_sports to fetch available sport IDs.",
                "data": None,
            }

        try:
            schedule_data = await self.client.with_session_retry(
                self.client.get_club_schedule,
                session_id=session_id,
                club_id=club_id,
                sport_id=sport_id,
                date=date,
            )

            if not schedule_data:
                return {
                    "success": False,
                    "message": "Failed to retrieve schedule data.",
                    "data": None,
                }
            json_data = json.loads(schedule_data)
            html = json_data.get("schedule")

            schedules = ScheduleParser.parse_schedules(
                html=html,
            )
            if schedules:
                courts = []
                for sched in schedules:
                    if int(sched["sport"]) == int(sport_id):
                        courts_data = sched["data"]
                        for c in courts_data:
                            courts.append(
                                Court(
                                    number=c["number"], availability=c["availability"]
                                )
                            )
                        schedule = Schedule(
                            club_id=club_id,
                            sport_id=sport_id,
                            date=date,
                            courts=courts,
                        )
                        return {
                            "success": True,
                            "message": "Schedule retrieved successfully",
                            "data": schedule.model_dump(),
                        }

            # missing schedule data, all courts are unavailable
            club_info = await self.client.with_session_retry(
                self.client.get_club_info, club_id=club_id
            )
            empty_hours = ScheduleParser.parse_schedules(club_info)
            return {
                "success": True,
                "message": "Empty schedule data. Booking unavailable",
                "data": empty_hours,
            }

        except ApiErrorException as e:
            return {
                "success": False,
                "message": f"Failed to get schedule: {e.message}",
                "data": None,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "data": None,
            }


# Global endpoint instance
schedule_endpoint = ScheduleEndpoint()
