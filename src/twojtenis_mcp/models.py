"""Data models for TwojTenis MCP server."""

from datetime import datetime
from enum import IntEnum
from typing import (
    Any,
)

from pydantic import BaseModel, Field


class SportId(IntEnum):
    """Enumeration of supported sport IDs."""

    TENNIS_SQUASH = 12
    BADMINTON = 84
    TENNIS = 70

    def __str__(self) -> str:
        return self.name.lower()

    def model_dump(
        self,
    ) -> dict[str, Any]:
        return {i.name: i.value for i in SportId}


class Club(BaseModel):
    """Represents a tennis/badminton club."""

    id: str = Field(..., description="Unique club identifier")
    name: str = Field(..., description="Club name")
    address: str = Field(..., description="Club address")
    phone: str = Field(..., description="Club phone number")


class Court(BaseModel):
    """Represents a court within a club."""

    number: str = Field(..., description="Court name or number")
    availability: dict[str, bool] = Field(
        ..., description="Dictionary mapping time slots to availability status"
    )


class Schedule(BaseModel):
    """Represents court availability schedule for a club."""

    club_id: str = Field(..., description="Club identifier")
    sport_id: SportId = Field(..., description="Sport identifier")
    date: str = Field(..., description="Date in DD.MM.YYYY format")
    courts: list[Court] = Field(..., description="List of courts with availability")


class Reservation(BaseModel):
    """Represents a court reservation."""

    user_id: str = Field(..., description="User identifier (PHPSESSID)")
    club_id: str = Field(..., description="Club identifier")
    court_number: str = Field(..., description="Court number")
    date: str = Field(..., description="Date in DD.MM.YYYY format")
    hour: str = Field(..., description="Hour in HH:MM format")
    sport_id: SportId | None = Field(SportId.BADMINTON, description="Sport identifier")


class UserSession(BaseModel):
    """Represents user session information."""

    phpsessid: str = Field(..., description="PHP session ID")
    expires_at: datetime | None = Field(
        None, description="Session expiration time (not used in new approach)"
    )
    is_active: bool = Field(True, description="Whether session is currently active")
    email: str | None = Field(None, description="User email")


class ApiError(BaseModel):
    """Represents an API error response."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: dict | None = Field(None, description="Additional error details")


class ApiErrorException(Exception):
    """Exception class for API errors that uses ApiError model for data."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        """Initialize the exception with error details."""
        super().__init__(f"[{code}] {message}")
        self.error = ApiError(code=code, message=message, details=details)
        self.code = code
        self.message = message
        self.details = details


class ReservationRequest(BaseModel):
    """Represents a reservation request."""

    club_id: str = Field(..., description="Club identifier")
    court_number: str = Field(..., description="Court number")
    date: str = Field(..., description="Date in DD.MM.YYYY format")
    hour: str = Field(..., description="Hour in HH:MM format")
    sport_id: SportId = Field(..., description="Sport identifier")


class DeleteReservationRequest(BaseModel):
    """Represents a reservation deletion request."""

    club_id: str = Field(..., description="Club identifier")
    court_number: str = Field(..., description="Court number")
    date: str = Field(..., description="Date in DD.MM.YYYY format")
    hour: str = Field(..., description="Hour in HH:MM format")
