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
        CourtBooking(
            court="1", date="27.12.2025", time_start="21:00", time_end="21:30"
        ),
        CourtBooking(
            court="2", date="27.12.2025", time_start="21:00", time_end="21:30"
        ),
    ]

    assert len(bookings) == 2
    assert bookings[0].court == "1"
    assert bookings[1].court == "2"
    assert all(b.date == "27.12.2025" for b in bookings)
    assert all(b.time_start == "21:00" for b in bookings)
    assert all(b.time_end == "21:30" for b in bookings)


@pytest.mark.asyncio
async def test_make_bulk_reservation_partial_failure():
    """Test bulk reservation with partial failure (some courts unavailable)."""
    from unittest.mock import AsyncMock, patch
    from twojtenis_mcp.endpoints.reservations import reservations_endpoint

    # Mock get_reservations at the endpoint level to return only one successful booking
    # (simulating one court/time slot unavailable)
    # The two bookings have different times, so only one will match
    mock_reservations = [
        {
            "booking_id": "123456",
            "date": "27.12.2025",
            "time": "21:00 - 21:30",
            "club_name": "Test Club",
            "court": "1",
        }
        # Note: Only the 21:00 slot is returned, the 22:00 slot was unavailable
    ]

    # Mock make_bulk_reservation client call
    async def mock_with_session_retry(func, **kwargs):
        if "court_bookings" in kwargs:
            return None
        return None

    with patch.object(
        reservations_endpoint.client, "with_session_retry", side_effect=mock_with_session_retry
    ):
        # Patch the endpoint's get_reservations method directly
        with patch.object(
            reservations_endpoint, "get_reservations", return_value=mock_reservations
        ):
            bookings = [
                {
                    "court": "1",
                    "date": "27.12.2025",
                    "time_start": "21:00",
                    "time_end": "21:30",
                },
                {
                    "court": "1",
                    "date": "27.12.2025",
                    "time_start": "22:00",
                    "time_end": "22:30",
                },
            ]

            result = await reservations_endpoint.make_bulk_reservation(
                session_id="test_session",
                club_num=90,
                sport_id=84,
                court_bookings=bookings,
            )

    # Verify partial success response
    assert result["success"] is True  # At least one booking succeeded
    assert "Partial bulk reservation" in result["message"]
    assert "1 court(s) booked" in result["message"]
    assert "1 court(s) unavailable" in result["message"]

    # Verify the reservation details
    assert "reservation" in result
    assert result["reservation"]["count"] == 2
    bookings_result = result["reservation"]["bookings"]

    # Find the bookings by time slot
    booking_21 = next(b for b in bookings_result if b["time_start"] == "21:00")
    booking_22 = next(b for b in bookings_result if b["time_start"] == "22:00")

    # Verify 21:00 slot is marked as successful with booking_id
    assert booking_21["success"] is True
    assert booking_21["booking_id"] == "123456"

    # Verify 22:00 slot is marked as failed without booking_id
    assert booking_22["success"] is False
    assert "booking_id" not in booking_22


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
