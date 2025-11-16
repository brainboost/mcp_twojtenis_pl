"""Tests for the ScheduleParser class."""

import json
import os

import pytest

from src.twojtenis_mcp.schedule_parser import ScheduleParser


class TestScheduleParser:
    """Test cases for ScheduleParser."""

    def test_parse_schedule_badminton_case_1(self):
        """Test parsing badminton schedule for case 1."""
        base_dir = os.path.dirname(os.path.abspath(__file__)) + "/data"

        # Load test input
        with open(os.path.join(base_dir, "test_input_1.json"), encoding="utf-8") as f:
            input_data = json.load(f)

        html = input_data.get("schedule")

        # Load expected output
        with open(os.path.join(base_dir, "test_output_1.json"), encoding="utf-8") as f:
            expected_output = json.load(f)

        result = ScheduleParser.parse_schedules(html=html)
        assert result is not None

        result_courts = []
        for sched in result:
            if int(sched["sport"]) == 84:
                result_courts = sched["data"]

        for i, expected in enumerate(expected_output):
            assert result_courts[i] == expected

    def test_parse_schedule_badminton_case_2(self):
        """Test parsing badminton schedule for case 2."""
        base_dir = os.path.dirname(os.path.abspath(__file__)) + "/data"

        # Load test input
        with open(os.path.join(base_dir, "test_input_2.json"), encoding="utf-8") as f:
            input_data = json.load(f)

        html = input_data.get("schedule")

        # Load expected output
        with open(os.path.join(base_dir, "test_output_2.json"), encoding="utf-8") as f:
            expected_output = json.load(f)

        result = ScheduleParser.parse_schedules(html=html)
        assert result is not None

        result_courts = []
        for sched in result:
            if int(sched["sport"]) == 12:
                result_courts = sched["data"]

        for i, expected in enumerate(expected_output):
            assert result_courts[i] == expected


if __name__ == "__main__":
    pytest.main()
