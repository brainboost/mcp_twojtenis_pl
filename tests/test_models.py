"""Tests for data models."""

from datetime import datetime

from twojtenis_mcp.models import (
    ApiError,
    ApiErrorException,
    Club,
    Court,
    DeleteReservationRequest,
    Reservation,
    ReservationRequest,
    Schedule,
    SportId,
    UserSession,
)


class TestClub:
    """Test Club model."""

    def test_club_creation(self):
        """Test creating a club."""
        club = Club(
            id="blonia_sport",
            name="Błonia Sport",
            address="al. 3 Maja 57",
            phone="+48728871400",
        )

        assert club.id == "blonia_sport"
        assert club.name == "Błonia Sport"
        assert club.address == "al. 3 Maja 57"
        assert club.phone == "+48728871400"

    def test_club_serialization(self):
        """Test club serialization."""
        club = Club(
            id="test_club",
            name="Test Club",
            address="Test Address",
            phone="+48123456789",
        )

        data = club.model_dump()
        assert data["id"] == "test_club"
        assert data["name"] == "Test Club"
        assert data["address"] == "Test Address"
        assert data["phone"] == "+48123456789"


class TestCourt:
    """Test Court model."""

    def test_court_creation(self):
        """Test creating a court."""
        availability = {"07:00": True, "07:30": False, "08:00": True}

        court = Court(number="Kort 1", availability=availability)

        assert court.number == "Kort 1"
        assert court.availability == availability
        assert court.availability["07:00"] is True
        assert court.availability["07:30"] is False

    def test_court_serialization(self):
        """Test court serialization."""
        availability = {"10:00": True, "10:30": False}
        court = Court(number="Kort 2", availability=availability)

        data = court.model_dump()
        assert data["number"] == "Kort 2"
        assert data["availability"] == availability


class TestSchedule:
    """Test Schedule model."""

    def test_schedule_creation(self):
        """Test creating a schedule."""
        courts = [
            Court(number="Kort 1", availability={"10:00": True}),
            Court(number="Kort 2", availability={"10:00": False}),
        ]

        schedule = Schedule(
            club_id="test_club",
            sport_id=SportId.BADMINTON,
            date="24.09.2025",
            courts=courts,
        )

        assert schedule.club_id == "test_club"
        assert schedule.sport_id == 84
        assert schedule.date == "24.09.2025"
        assert len(schedule.courts) == 2
        assert schedule.courts[0].number == "Kort 1"
        assert schedule.courts[1].number == "Kort 2"


class TestReservation:
    """Test Reservation model."""

    def test_reservation_creation(self):
        """Test creating a reservation."""
        reservation = Reservation(
            user_id="test_session",
            club_id="test_club",
            court_number="Kort 1",
            date="24.09.2025",
            hour="10:00",
            sport_id=SportId.BADMINTON,
        )

        assert reservation.user_id == "test_session"
        assert reservation.club_id == "test_club"
        assert reservation.court_number == "Kort 1"
        assert reservation.date == "24.09.2025"
        assert reservation.hour == "10:00"
        assert reservation.sport_id == 84


class TestUserSession:
    """Test UserSession model."""

    def test_user_session_creation(self):
        """Test creating a user session."""
        expires_at = datetime.now()
        session = UserSession(
            phpsessid="test_session_id",
            expires_at=expires_at,
            is_active=True,
            email="test@example.com",
        )

        assert session.phpsessid == "test_session_id"
        assert session.expires_at == expires_at
        assert session.is_active is True
        assert session.email == "test@example.com"


class TestApiError:
    """Test ApiError model."""

    def test_api_error_creation(self):
        """Test creating an API error."""
        error = ApiError(
            code="TEST_ERROR", message="Test error message", details={"field": "value"}
        )

        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.details == {"field": "value"}

    def test_api_error_without_details(self):
        """Test creating an API error without details."""
        error = ApiErrorException(code="SIMPLE_ERROR", message="Simple error message")

        assert error.code == "SIMPLE_ERROR"
        assert error.message == "Simple error message"
        assert error.details is None


class TestReservationRequest:
    """Test ReservationRequest model."""

    def test_reservation_request_creation(self):
        """Test creating a reservation request."""
        request = ReservationRequest(
            club_id="test_club",
            court_number="Kort 1",
            date="24.09.2025",
            hour="10:00",
            sport_id=SportId.BADMINTON,
        )

        assert request.club_id == "test_club"
        assert request.court_number == "Kort 1"
        assert request.date == "24.09.2025"
        assert request.hour == "10:00"
        assert request.sport_id == 84


class TestDeleteReservationRequest:
    """Test DeleteReservationRequest model."""

    def test_delete_reservation_request_creation(self):
        """Test creating a delete reservation request."""
        request = DeleteReservationRequest(
            club_id="test_club", court_number="Kort 1", date="24.09.2025", hour="10:00"
        )

        assert request.club_id == "test_club"
        assert request.court_number == "Kort 1"
        assert request.date == "24.09.2025"
        assert request.hour == "10:00"
