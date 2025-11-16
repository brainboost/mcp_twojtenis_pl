"""Schedule parsing utilities for TwojTenis MCP server."""

import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from twojtenis_mcp.models import ApiErrorException

from .utils import extract_id_from_url

logger = logging.getLogger(__name__)


class ScheduleParser:
    """Parser for court schedule data from TwojTenis.pl."""

    @staticmethod
    def parse_schedules(html: str) -> list | None:
        """
        Parses an HTML 'schedule' block and returns data with
        a collection of courts with 30m availability term, combined by sports.

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
            On missing schedule data returns None
        """
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        schedule_list: list = []

        # locate a schedule block
        for sched in soup.find_all("div", class_="schedule"):
            sport = ScheduleParser.get_sport_from_id(str(sched["id"]))
            cols = sched.find_all("div", class_="schedule_col")
            courts = ScheduleParser._extract_schedule_table(cols)
            schedule_list.append({"sport": sport, "data": courts})

        return schedule_list

    @staticmethod
    def parse_club_info(html: str) -> dict[str, Any] | None:
        """
        Parses an HTML club info page and returns data as dictionary.

        Args:
            json_str (str): JSON document as a string.

        On missing html returns None
        """
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        sport_list: list = []
        # parse sports list
        well = soup.find("div", class_="well")
        if well is None:
            raise ApiErrorException(
                code="NO_SESSION",
                message="No active session available. HTML parsing error. No div 'well'",
            )

        btn_group = well.find("div", class_="btn-group")
        if btn_group is None:
            raise Exception("HTML parsing error. No 'btn_group' div")
        for sprtch in btn_group.find_all("span", class_="sprtch"):
            sport_id = ScheduleParser.get_sport_from_id(str(sprtch["id"]))
            sport_name = sprtch.text
            sport_list.append({"id": sport_id, "name": sport_name})
        # parse working hours
        times = []
        sched = soup.find("div", class_="schedule")
        if sched is not None:
            col = sched.find("div", class_="schedule_col")
            if col is not None:
                times = [
                    elem.get_text().strip()
                    for elem in col.find_all("div", class_="hourboxer")
                ]
        return {"sports": sport_list, "times": times}

    @staticmethod
    def parse_reservations(input: str) -> list[dict[str, Any]] | None:
        if not input:
            return None

        soup = BeautifulSoup(input, "html.parser")
        resrvations: list = []
        dashboard = soup.find("div", id="dashboard_content")
        if dashboard is None:
            raise ApiErrorException(
                code="NO_SESSION",
                message="No active session available. HTML parsing error. No div 'dashboard_content'",
            )

        for box in dashboard.find_all("div", class_="rsv_box"):
            link = box.find("a").attrs["href"]  # type: ignore
            booking_id = extract_id_from_url(link)  # type: ignore

            date_time = box.find("p", class_="al_center").get_text("_")  # type: ignore
            date, time = date_time.split("_", 2)

            club_img = box.find("img").attrs["src"]  # type: ignore
            club_no = extract_id_from_url(club_img)  # type: ignore

            name = box.find("h3", class_="al_center").text  # type: ignore
            resrvations.append(
                {
                    "booking_id": booking_id,
                    "date": date.strip(),
                    "time": time.strip(),
                    "club_num": club_no,
                    "club_name": name.strip(),
                }
            )

        return resrvations

    @staticmethod
    def parse_reservation(input: str) -> dict[str, Any] | None:
        if not input:
            return None

        soup = BeautifulSoup(input, "html.parser")

        container = soup.find("div", id="site_content")
        if container is None:
            raise ApiErrorException(
                code="NO_SESSION",
                message="No active session available. HTML parsing error. No div 'site_content'",
            )

        # <div id="site_breadcrumbs" class="al_clear">
        for box in container.find_all("div", id="site_breadcrumbs"):
            links = box.find_all("a")
            club_id = extract_id_from_url(links[-2].attrs["href"])  # type: ignore
            club_name = links[-2].text  # type: ignore

        # <div class="well well-rsv well-full">
        well = container.find("div", class_="well-full")
        club_img = well.find("img", class_="club_emblem").attrs["src"]  # type: ignore
        club_num = extract_id_from_url(club_img)  # type: ignore

        tables = container.find_all("table", class_="table-rsv")
        # 0 - reservation table
        tr = tables[0].find("tbody").find("tr")  # type: ignore
        rows = tr.find_all("td")  # type: ignore
        date = rows[0].text.strip()
        time = rows[1].text.strip()
        labels_text = rows[2].get_text(separator=",").strip()
        cancel_dt = rows[3].text  # type: ignore
        labels = labels_text.replace(" ", "").replace("\n", " ").split(",", 3)
        sport = labels[0].strip()
        court = labels[2].strip()
        details = labels[-1].replace(",", " ").strip()
        # 1 - payments table
        tds = tables[1].find("tbody").find("tr").find_all("td")  # type: ignore
        pay_till = tds[-2].text
        price = tds[-1].text

        return {
            "club_id": club_id,  # type: ignore
            "club_name": club_name,  # type: ignore
            "club_num": club_num,
            "sport": sport,
            "court": court,
            "details": details,
            "date": date,
            "time": time,
            "cancel_till": cancel_dt,
            "price": price,
            "pay_till": pay_till,
        }

    @staticmethod
    def _extract_schedule_table(cols: list[Tag]):
        """Extract the time axis from the first column"""
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
            rows = col.find_all("div", class_="schedule_line")
            availability = {}
            for t, row in zip(times, rows, strict=False):
                # look for .reservation_closed in all children
                closed_cells = row.find_all(
                    attrs={"class": "reservation_closed"}, limit=1
                )
                has_closed_class = len(closed_cells) != 0
                if has_closed_class and closed_cells[0].get("style"):
                    style = closed_cells[0].get("style")
                    height_match = re.search(r"height:\s*(\d+)px", style)  # type: ignore
                    if height_match:
                        height = int(height_match.group(1))
                        closed_heigth = int(height / 41)
                        availability[t] = closed_heigth
                        continue
                availability[t] = 0

            courts.append(
                {
                    "number": name,
                    "availability": ScheduleParser._translate_availability(
                        availability
                    ),
                }
            )
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

    @staticmethod
    def _translate_availability(input: dict[str, int]) -> dict[str, bool]:
        """
        Translates availability codes to boolean values.

        - 0 means True (available)
        - n > 0 means False for this slot and the next n-1 slots

        Args:
            input: Dictionary mapping time slots to availability codes

        Returns:
            Dictionary mapping time slots to boolean availability
        """
        result = {}
        skip_count = 0

        for key, value in input.items():
            if skip_count > 0:
                # We're in a "skip" period from a previous non-zero value
                result[key] = False
                skip_count -= 1
            elif value == 0:
                # 0 means available
                result[key] = True
            else:
                # Positive number: this slot is False, plus next (value-1) slots
                result[key] = False
                skip_count = value - 1

        return result
