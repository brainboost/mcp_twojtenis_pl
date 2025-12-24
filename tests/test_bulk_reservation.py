"""Tests for bulk reservation functionality."""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from twojtenis_mcp.models import CourtBooking


def test_court_booking_model():
    """Test CourtBooking model validation."""
    # Valid booking
    booking = CourtBooking(
        court="1",
        date="27.12.2025",
        time_start="21:00",
        time_end="21:30",
    )
    assert booking.court == "1"
    assert booking.date == "27.12.2025"
    assert booking.time_start == "21:00"
    assert booking.time_end == "21:30"

    # Valid booking with different court
    booking2 = CourtBooking(
        court="2",
        date="27.12.2025",
        time_start="21:00",
        time_end="21:30",
    )
    assert booking2.court == "2"


def test_court_booking_model_missing_field():
    """Test CourtBooking model validation with missing field."""
    with pytest.raises(Exception):
        CourtBooking(
            court="1",
            date="27.12.2025",
            # Missing time_start
            time_end="21:30",
        )


def test_court_booking_from_dict():
    """Test creating CourtBooking from dictionary."""
    data = {
        "court": "3",
        "date": "27.12.2025",
        "time_start": "21:00",
        "time_end": "21:30",
    }
    booking = CourtBooking(**data)
    assert booking.court == "3"
    assert booking.date == "27.12.2025"
    assert booking.time_start == "21:00"
    assert booking.time_end == "21:30"


@pytest.mark.asyncio
async def test_make_bulk_reservation_validation_empty_list():
    """Test bulk reservation validation with empty list."""
    from twojtenis_mcp.endpoints.reservations import reservations_endpoint

    result = await reservations_endpoint.make_bulk_reservation(
        session_id="test_session",
        club_num=90,
        sport_id=84,
        court_bookings=[],
    )
    assert result["success"] is False
    assert "No bookings provided" in result["message"]


@pytest.mark.asyncio
async def test_make_bulk_reservation_validation_invalid_date():
    """Test bulk reservation validation with invalid date."""
    from twojtenis_mcp.endpoints.reservations import reservations_endpoint

    invalid_bookings = [
        {
            "court": "1",
            "date": "2025-12-27",  # Wrong format - should be DD.MM.YYYY
            "time_start": "21:00",
            "time_end": "21:30",
        }
    ]

    result = await reservations_endpoint.make_bulk_reservation(
        session_id="test_session",
        club_num=90,
        sport_id=84,
        court_bookings=invalid_bookings,
    )
    assert result["success"] is False
    assert "Invalid date format" in result["message"]


@pytest.mark.asyncio
async def test_make_bulk_reservation_validation_invalid_time():
    """Test bulk reservation validation with invalid time."""
    from twojtenis_mcp.endpoints.reservations import reservations_endpoint

    invalid_bookings = [
        {
            "court": "1",
            "date": "27.12.2025",
            "time_start": "9:00",  # Wrong format - should be HH:MM
            "time_end": "21:30",
        }
    ]

    result = await reservations_endpoint.make_bulk_reservation(
        session_id="test_session",
        club_num=90,
        sport_id=84,
        court_bookings=invalid_bookings,
    )
    assert result["success"] is False
    assert "Invalid time format" in result["message"]


def test_bulk_reservation_example_data():
    """Test the example data from the user's request."""
    bookings = [
        CourtBooking(court="1", date="27.12.2025", time_start="21:00", time_end="21:30"),
        CourtBooking(court="2", date="27.12.2025", time_start="21:00", time_end="21:30"),
    ]

    assert len(bookings) == 2
    assert bookings[0].court == "1"
    assert bookings[1].court == "2"
    assert all(b.date == "27.12.2025" for b in bookings)
    assert all(b.time_start == "21:00" for b in bookings)
    assert all(b.time_end == "21:30" for b in bookings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
