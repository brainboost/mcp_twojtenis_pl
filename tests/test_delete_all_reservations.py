"""Tests for delete_all_reservations functionality."""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from twojtenis_mcp.endpoints.reservations import reservations_endpoint


@pytest.mark.asyncio
async def test_delete_all_reservations_empty_list():
    """Test delete_all_reservations when user has no reservations."""

    # Mock get_reservations to return empty list
    async def mock_get_reservations(session_id: str):
        return []

    original_get_reservations = reservations_endpoint.get_reservations
    reservations_endpoint.get_reservations = mock_get_reservations

    result = await reservations_endpoint.delete_all_reservations(
        session_id="test_session"
    )

    # Restore original method
    reservations_endpoint.get_reservations = original_get_reservations

    assert result["success"] is True
    assert result["deleted_count"] == 0
    assert result["deleted_booking_ids"] == []
    assert "No reservations found" in result["message"]


@pytest.mark.asyncio
async def test_delete_all_reservations_single_success():
    """Test delete_all_reservations with a single successful deletion."""

    # Mock get_reservations to return one reservation
    async def mock_get_reservations(session_id: str):
        return [{"booking_id": "abc123", "court": "1", "date": "01.01.2025"}]

    # Mock client.delete_reservation to return True
    async def mock_delete_reservation(session_id: str, booking_id: str):
        return True

    original_get_reservations = reservations_endpoint.get_reservations
    original_client_delete = reservations_endpoint.client.delete_reservation

    reservations_endpoint.get_reservations = mock_get_reservations
    reservations_endpoint.client.delete_reservation = mock_delete_reservation

    result = await reservations_endpoint.delete_all_reservations(
        session_id="test_session"
    )

    # Restore original methods
    reservations_endpoint.get_reservations = original_get_reservations
    reservations_endpoint.client.delete_reservation = original_client_delete

    assert result["success"] is True
    assert result["deleted_count"] == 1
    assert result["deleted_booking_ids"] == ["abc123"]
    assert result["failed_booking_ids"] == []
    assert "Successfully deleted all 1 reservation" in result["message"]


@pytest.mark.asyncio
async def test_delete_all_reservations_multiple_success():
    """Test delete_all_reservations with multiple successful deletions."""

    # Mock get_reservations to return three reservations
    async def mock_get_reservations(session_id: str):
        return [
            {"booking_id": "abc123", "court": "1", "date": "01.01.2025"},
            {"booking_id": "def456", "court": "2", "date": "01.01.2025"},
            {"booking_id": "ghi789", "court": "3", "date": "01.01.2025"},
        ]

    # Mock client.delete_reservation to return True
    async def mock_delete_reservation(session_id: str, booking_id: str):
        return True

    original_get_reservations = reservations_endpoint.get_reservations
    original_client_delete = reservations_endpoint.client.delete_reservation

    reservations_endpoint.get_reservations = mock_get_reservations
    reservations_endpoint.client.delete_reservation = mock_delete_reservation

    result = await reservations_endpoint.delete_all_reservations(
        session_id="test_session"
    )

    # Restore original methods
    reservations_endpoint.get_reservations = original_get_reservations
    reservations_endpoint.client.delete_reservation = original_client_delete

    assert result["success"] is True
    assert result["deleted_count"] == 3
    assert set(result["deleted_booking_ids"]) == {"abc123", "def456", "ghi789"}
    assert result["failed_booking_ids"] == []
    assert "Successfully deleted all 3 reservation" in result["message"]


@pytest.mark.asyncio
async def test_delete_all_reservations_partial_failure():
    """Test delete_all_reservations with some failed deletions."""

    # Mock get_reservations to return three reservations
    async def mock_get_reservations(session_id: str):
        return [
            {"booking_id": "abc123", "court": "1", "date": "01.01.2025"},
            {"booking_id": "def456", "court": "2", "date": "01.01.2025"},
            {"booking_id": "ghi789", "court": "3", "date": "01.01.2025"},
        ]

    # Mock client.delete_reservation to fail for def456
    async def mock_delete_reservation(session_id: str, booking_id: str):
        return booking_id != "def456"

    original_get_reservations = reservations_endpoint.get_reservations
    original_client_delete = reservations_endpoint.client.delete_reservation

    reservations_endpoint.get_reservations = mock_get_reservations
    reservations_endpoint.client.delete_reservation = mock_delete_reservation

    result = await reservations_endpoint.delete_all_reservations(
        session_id="test_session"
    )

    # Restore original methods
    reservations_endpoint.get_reservations = original_get_reservations
    reservations_endpoint.client.delete_reservation = original_client_delete

    assert result["success"] is False  # Not all succeeded
    assert result["deleted_count"] == 2
    assert set(result["deleted_booking_ids"]) == {"abc123", "ghi789"}
    assert result["failed_booking_ids"] == ["def456"]
    assert "Deleted 2 of 3 reservation" in result["message"]
    assert "1 deletion(s) failed" in result["message"]


@pytest.mark.asyncio
async def test_delete_all_reservations_all_fail():
    """Test delete_all_reservations when all deletions fail."""

    # Mock get_reservations to return two reservations
    async def mock_get_reservations(session_id: str):
        return [
            {"booking_id": "abc123", "court": "1", "date": "01.01.2025"},
            {"booking_id": "def456", "court": "2", "date": "01.01.2025"},
        ]

    # Mock client.delete_reservation to always fail
    async def mock_delete_reservation(session_id: str, booking_id: str):
        return False

    original_get_reservations = reservations_endpoint.get_reservations
    original_client_delete = reservations_endpoint.client.delete_reservation

    reservations_endpoint.get_reservations = mock_get_reservations
    reservations_endpoint.client.delete_reservation = mock_delete_reservation

    result = await reservations_endpoint.delete_all_reservations(
        session_id="test_session"
    )

    # Restore original methods
    reservations_endpoint.get_reservations = original_get_reservations
    reservations_endpoint.client.delete_reservation = original_client_delete

    assert result["success"] is False
    assert result["deleted_count"] == 0
    assert result["deleted_booking_ids"] == []
    assert set(result["failed_booking_ids"]) == {"abc123", "def456"}
    assert "Failed to delete any of the 2 reservation" in result["message"]


@pytest.mark.asyncio
async def test_delete_all_reservations_missing_booking_id():
    """Test delete_all_reservations handles reservations without booking_id."""

    # Mock get_reservations to return reservations with missing booking_id
    async def mock_get_reservations(session_id: str):
        return [
            {"booking_id": "abc123", "court": "1", "date": "01.01.2025"},
            {"court": "2", "date": "01.01.2025"},  # No booking_id
        ]

    # Mock client.delete_reservation to return True
    async def mock_delete_reservation(session_id: str, booking_id: str):
        return True

    original_get_reservations = reservations_endpoint.get_reservations
    original_client_delete = reservations_endpoint.client.delete_reservation

    reservations_endpoint.get_reservations = mock_get_reservations
    reservations_endpoint.client.delete_reservation = mock_delete_reservation

    result = await reservations_endpoint.delete_all_reservations(
        session_id="test_session"
    )

    # Restore original methods
    reservations_endpoint.get_reservations = original_get_reservations
    reservations_endpoint.client.delete_reservation = original_client_delete

    assert result["success"] is True
    assert result["deleted_count"] == 1
    assert result["deleted_booking_ids"] == ["abc123"]
    assert result["failed_booking_ids"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
