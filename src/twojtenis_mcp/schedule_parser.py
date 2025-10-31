"""Schedule parsing utilities for TwojTenis MCP server."""

import json
import logging

from bs4 import BeautifulSoup

from .models import Schedule, SportId

logger = logging.getLogger(__name__)


class ScheduleParser:
    """Parser for court schedule data from TwojTenis.pl."""

    @staticmethod
    def parse_schedule(
        json_str: str,
        club_id: str,
        sport_id: int,
        date: str,
        sport_name: str,
    ) -> Schedule | None:
        """
        Parses a JSON string containing an HTML 'schedule' field and returns
        a list of courts with half‐hour availability.

        Args:
            json_str (str): JSON document as a string.
            club_id (str): Club identifier
            sport_id (int): Sport identifier
            date (str): Date in DD.MM.YYYY format
            sport_name (str): Name of sport to filter for

        Returns:
            Schedule object with courts and their availability
        """
        data = json.loads(json_str)
        html = data.get("schedule")
        if not html:
            raise ValueError("Missing 'schedule' field in JSON")

        soup = BeautifulSoup(html, "html.parser")

        # 1. Locate the schedule block for the specified sport
        sport_div = None
        for sched in soup.find_all("div", class_="schedule"):
            # Check if this schedule contains the sport we're looking for
            # Look for any strong tag that contains the sport name
            headers = sched.find_all("strong")
            for header in headers:
                header_text = header.get_text().strip().lower()
                # Check if sport name is in header text or if header text contains sport name
                if (
                    sport_name.lower() in header_text
                    or header_text in sport_name.lower()
                ):
                    sport_div = sched
                    break
            if sport_div:
                break

        if sport_div is None:
            raise RuntimeError(f"{sport_name.capitalize()} schedule not found in HTML")

        cols = sport_div.find_all("div", class_="schedule_col")

        # 2. Extract the time axis from the first column
        time_col = cols[0]
        times = [
            elem.get_text().strip()
            for elem in time_col.find_all("div", class_="hourboxer")
        ]

        courts = []
        # 3. Middle columns represent each court; last column is a mirror of the times
        # Handle both cases: with and without the last mirror column
        court_cols = cols[1:-1] if len(cols) > 2 else cols[1:]

        for col in court_cols:
            # Court header: e.g. "Badminton 1", "Hala 1", etc.
            header = col.find("strong")
            if not header:
                continue
            name = header.get_text().strip()

            # Use the full court name instead of just the number
            court_name = name

            # Each time slot should have a corresponding row or schedule_row element
            availability = {}

            # Get all the schedule_row elements in the column
            _schedule_rows = col.find_all("div", class_="schedule_row")

            # Now process each time slot
            for i, time_slot in enumerate(times):
                # Default to available
                available = True

                # Find the schedule_row element for this time slot
                # The ID pattern is: bidi_{club_id}_{court_index}_{hour}_{minute}
                target_id = f"bidi_84_1_1_{i // 2:02d}_{(i % 2) * 30:02d}"
                target_row = col.find("div", id=target_id)

                if target_row:
                    # Check if this row has the reservation_closed class directly
                    if "reservation_closed" in target_row.get("class", []):  # type: ignore
                        available = False
                    else:
                        # Check if any child element has the 'reservation_closed' class
                        child_elements = target_row.find_all()
                        is_closed = False
                        for child in child_elements:
                            if child.has_attr("class"):
                                classes = child.get("class")
                                if (
                                    isinstance(classes, list)
                                    and "reservation_closed" in classes
                                ):
                                    is_closed = True
                                    break
                        # 'reservation_bg' ⇒ available, 'reservation_closed' ⇒ occupied
                        available = not is_closed
                else:
                    # If we couldn't find the matching element, assume not available
                    available = False

                availability[time_slot] = available

            courts.append({"number": court_name, "availability": availability})

        return Schedule(
            club_id=club_id, sport_id=SportId(sport_id), date=date, courts=courts
        )

    @staticmethod
    def parse_schedules(json_str: str) -> list | None:
        """
        Parses a JSON string containing an HTML 'schedule' field and returns
        a list of courts with half/hour availability window.

        Args:
            json_str (str): JSON document as a string.

        Returns:
            list of dict: [
                {
                "sport": int,
                "data: {
                        "number": str,
                        "availability": {
                            "07:00": bool,
                            "07:30": bool,
                            ...,
                            "22:30": bool
                        }
                    }
                }, ...
            ]
        """
        data = json.loads(json_str)
        html = data.get("schedule")
        if not html:
            raise ValueError("Missing 'schedule' field in JSON")

        soup = BeautifulSoup(html, "html.parser")
        schedule_list: list = []

        # Locate a schedule block
        for sched in soup.find_all("div", class_="schedule"):
            sport = ScheduleParser.get_sport_from_id(str(sched["id"]))
            cols = sched.find_all("div", class_="schedule_col")
            courts = ScheduleParser.extract_table_data(cols)
            schedule_list.append({"sport": sport, "data": courts})

        return schedule_list

    @staticmethod
    def extract_table_data(cols):
        # Extract the time axis from the first column
        time_col = cols[0]
        times = [
            elem.get_text().strip()
            for elem in time_col.find_all("div", class_="hourboxer")
        ]

        courts = []
        # Middle columns represent each court; last column is a mirror of the times
        for col in cols[1:-1]:
            # Court header: e.g. "Badminton 1"
            header = col.find("strong")
            if not header:
                continue
            name = header.get_text().strip()

            # Each .schedule_line corresponds to one timeslot, in the same order as `times`
            # but we need to skip 1st line bc a header also has .schedule_line
            rows = col.find_all("div", class_="schedule_line")
            availability = {}
            for t, row in zip(times, rows[1:], strict=False):
                # look for .reservation_closed in all children
                is_closed = row.find_all(attrs={"class": "reservation_closed"}, limit=1)
                availability[t] = not is_closed

            courts.append({"number": name, "availability": availability})
        return courts

    @staticmethod
    def get_sport_from_id(id_str: str) -> str:
        """Extracts sport_id out of the string from the html id attribute like cl_70_1

        Args:
            id_str: input id string

        Returns:
            Sport ID
        """
        return id_str.split("_", maxsplit=2)[1]

    # Class constant for sport names mapping - defined once at class level
    _SPORT_NAMES = {
        SportId.BADMINTON.value: "badminton",
        SportId.TENNIS.value: "tennis",
        SportId.TENNIS_SQUASH.value: "tennis_squash",
    }

    @classmethod
    def get_sport_name_by_id(cls, sport_id: int) -> str:
        """Get sport name by sport ID.

        Args:
            sport_id: Sport identifier

        Returns:
            Sport name

        Raises:
            ValueError: If sport_id is not a positive integer
        """
        # Validate input
        if not isinstance(sport_id, int) or sport_id <= 0:
            raise ValueError(
                f"Invalid sport_id: {sport_id}. Must be a positive integer."
            )

        # Use the class constant for better performance and maintainability
        return cls._SPORT_NAMES.get(sport_id, f"sport_{sport_id}")

    @classmethod
    def is_valid_sport_id(cls, sport_id: int) -> bool:
        """Check if a sport ID is valid and supported.

        Args:
            sport_id: Sport identifier to validate

        Returns:
            True if the sport ID is valid and supported, False otherwise
        """
        try:
            if not isinstance(sport_id, int) or sport_id <= 0:
                return False
            return sport_id in cls._SPORT_NAMES
        except Exception:
            return False

    @classmethod
    def get_all_supported_sports(cls) -> dict[int, str]:
        """Get all supported sport IDs and their names.

        Returns:
            Dictionary mapping sport IDs to sport names
        """
        return cls._SPORT_NAMES.copy()

    @staticmethod
    def parse_reservations(html_content: str) -> list[dict]:
        """Parse reservations from HTML response.

        Args:
            html_content: HTML content containing reservations

        Returns:
            List of reservation dictionaries
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            reservations = []

            # This is a placeholder implementation
            # The actual parsing would depend on the HTML structure of the reservations page
            reservation_elements = soup.find_all("div", class_="reservation")

            for _element in reservation_elements:
                # Extract reservation details
                # This would need to be adapted to the actual HTML structure
                reservation = {
                    "club_id": "",
                    "court_number": 0,
                    "date": "",
                    "hour": "",
                    "sport_id": 0,
                }
                reservations.append(reservation)

            logger.info(f"Parsed {len(reservations)} reservations")
            return reservations

        except Exception as e:
            logger.error(f"Error parsing reservations: {e}")
            return []
