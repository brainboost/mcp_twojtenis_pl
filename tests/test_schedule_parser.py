"""Tests for the ScheduleParser class."""

import json
import os

import pytest

from src.twojtenis_mcp.models import SportId
from src.twojtenis_mcp.schedule_parser import ScheduleParser


class TestScheduleParser:
    """Test cases for ScheduleParser."""

    def test_parse_schedule_badminton_case_1(self):
        """Test parsing badminton schedule for case 1."""
        base_dir = os.path.dirname(os.path.abspath(__file__)) + "/data"

        # Load test input
        with open(os.path.join(base_dir, "test_input_1.json"), encoding="utf-8") as f:
            input_data = json.load(f)

        # Load expected output
        with open(os.path.join(base_dir, "test_output_1.json"), encoding="utf-8") as f:
            expected_output = json.load(f)

        result = ScheduleParser.parse_schedules(json_str=json.dumps(input_data))
        assert result is not None

        result_courts = []
        for sched in result:
            if int(sched["sport"]) == int(SportId.BADMINTON):
                result_courts = sched["data"]

        for i, expected in enumerate(expected_output):
            assert result_courts[i] == expected

    def test_parse_schedule_badminton_case_2(self):
        """Test parsing badminton schedule for case 2."""
        base_dir = os.path.dirname(os.path.abspath(__file__)) + "/data"

        # Load test input
        with open(os.path.join(base_dir, "test_input_2.json"), encoding="utf-8") as f:
            input_data = json.load(f)

        # Load expected output
        with open(os.path.join(base_dir, "test_output_2.json"), encoding="utf-8") as f:
            expected_output = json.load(f)

        # Parse the schedule
        result = ScheduleParser.parse_schedules(json_str=json.dumps(input_data))
        assert result is not None

        result_courts = []
        for sched in result:
            if int(sched["sport"]) == int(SportId.TENNIS_SQUASH):
                result_courts = sched["data"]

        for i, expected in enumerate(expected_output):
            assert result_courts[i] == expected

    def test_get_sport_name_by_id(self):
        """Test getting sport name by ID."""
        assert (
            ScheduleParser.get_sport_name_by_id(SportId.BADMINTON.value) == "badminton"
        )
        assert ScheduleParser.get_sport_name_by_id(SportId.TENNIS.value) == "tennis"
        assert (
            ScheduleParser.get_sport_name_by_id(SportId.TENNIS_SQUASH.value)
            == "tennis_squash"
        )
        assert ScheduleParser.get_sport_name_by_id(999) == "sport_999"

    def test_is_valid_sport_id(self):
        """Test validation of sport IDs."""
        assert ScheduleParser.is_valid_sport_id(SportId.BADMINTON.value)
        assert ScheduleParser.is_valid_sport_id(SportId.TENNIS.value)
        assert ScheduleParser.is_valid_sport_id(SportId.TENNIS_SQUASH.value)
        assert not ScheduleParser.is_valid_sport_id(999)
        assert not ScheduleParser.is_valid_sport_id(-1)
        assert not ScheduleParser.is_valid_sport_id("invalid")  # type: ignore

    def test_get_all_supported_sports(self):
        """Test getting all supported sports."""
        sports = ScheduleParser.get_all_supported_sports()
        assert SportId.BADMINTON.value in sports
        assert SportId.TENNIS.value in sports
        assert SportId.TENNIS_SQUASH.value in sports
        assert sports[SportId.BADMINTON.value] == "badminton"
        assert sports[SportId.TENNIS.value] == "tennis"
        assert sports[SportId.TENNIS_SQUASH.value] == "tennis_squash"

    def test_parse_reservations(self):
        """Test parsing reservations from HTML."""
        # This is a placeholder test since parse_reservations is not fully implemented
        html_content = "<div class='reservation'></div>"
        result = ScheduleParser.parse_reservations(html_content)
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main()
