"""Data models for TwojTenis MCP server."""

from datetime import datetime

from pydantic import BaseModel, Field


class SportId(BaseModel):
    """Represents a kind of sport."""

    id: int = Field(..., description="Unique Identifier")
    name: str = Field(..., description="Sport name")


class Club(BaseModel):
    """Represents a sporting club."""

    id: str = Field(..., description="Unique club identifier")
    num: int = Field(..., description="Numeric club identifier")
    name: str = Field(..., description="Club name")
    address: str = Field(..., description="Club address")
    phone: str = Field(..., description="Club phone number")
    sports: list[SportId] | None = Field(None, description="List of supported sports")


class Court(BaseModel):
    """Represents a court within a club."""

    number: str = Field(..., description="Court name or number")
    availability: dict[str, bool] = Field(
        ..., description="Dictionary mapping time slots to availability status"
    )


class Schedule(BaseModel):
    """Represents court availability schedule for a club."""

    club_id: str = Field(..., description="Club identifier")
    sport_id: int = Field(..., description="Sport identifier")
    date: str = Field(..., description="Date in DD.MM.YYYY format")
    courts: list[Court] = Field(..., description="List of courts with availability")


class Reservation(BaseModel):
    """Represents a court reservation."""

    booking_id: str = Field(..., description="Reservation identifier")
    user_id: str = Field(..., description="User identifier")
    club_id: str = Field(..., description="Club identifier")
    court_number: str = Field(..., description="Court number")
    date: str = Field(..., description="Date in DD.MM.YYYY format")
    hour: str = Field(..., description="Hour in HH:MM format")
    sport_id: int = Field(..., description="Sport identifier")


class UserSession(BaseModel):
    """Represents user session information."""

    phpsessid: str = Field(..., description="PHP session ID")
    expires_at: datetime = Field(..., description="Session expiration datetime")


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
    sport_id: int = Field(..., description="Sport identifier")


class DeleteReservationRequest(BaseModel):
    """Represents a reservation deletion request."""

    club_id: str = Field(..., description="Club identifier")
    court_number: str = Field(..., description="Court number")
    date: str = Field(..., description="Date in DD.MM.YYYY format")
    hour: str = Field(..., description="Hour in HH:MM format")
