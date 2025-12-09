"""Authentication and session management for TwojTenis MCP server."""

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import config
from .models import UserSession

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user authentication and session persistence."""

    def __init__(self):
        """Initialize session manager."""
        logger.info("Initialize session manager")
        self._session: UserSession | None = None
        self._session_file_path = Path("config/session.json")
        self._session_file_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize session manager and restore or create session.

        Returns:
            True if session is successfully initialized, False otherwise
        """
        # Try to load existing session
        return await self._load_session()

    async def _load_session(self) -> bool:
        """Load session from file.

        Returns:
            True if session was loaded successfully, False otherwise
        """
        try:
            if not self._session_file_path.exists():
                return False

            with open(self._session_file_path, encoding="utf-8") as f:
                session_data = json.load(f)

            if "expires_at" in session_data and session_data["expires_at"]:
                expires_at = session_data["expires_at"]
                session_data["expires_at"] = datetime.fromisoformat(expires_at)
            else:
                session_data["expires_at"] = None

            self._session = UserSession(**session_data)
            logger.info("Session loaded from file")
            return True

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load session from file: {e}")
            return False

    async def save_session(self, session_id: str) -> None:
        """Save current session to file."""
        await self.save_external_session(session_id)

    async def save_external_session(self, phpsessid: str) -> None:
        """Save externally obtained session ID.

        Args:
            phpsessid: PHP session ID obtained from external authentication
        """
        self._session = UserSession(
            phpsessid=phpsessid,
            expires_at=datetime.now(UTC) + timedelta(minutes=config.session_lifetime),
        )
        try:
            session_data = self._session.model_dump()

            if self._session.expires_at:
                session_data["expires_at"] = self._session.expires_at.isoformat()

            with open(self._session_file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            logger.info("External session saved to file")

        except (OSError, TypeError) as e:
            logger.error(f"Failed to save external session to file: {e}")

    async def get_session(self) -> UserSession | None:
        """Get current active session.

        Returns:
            Current session if active, None otherwise
        """
        add5min = datetime.now(UTC) + timedelta(minutes=5)
        if (
            self._session
            and self._session.expires_at
            and self._session.expires_at > add5min
        ):
            return self._session
        return None

    async def logout(self) -> None:
        """Logout and invalidate current session."""
        if self._session:
            self._session = None

        if self._session_file_path.exists():
            try:
                self._session_file_path.unlink()
                logger.info("Session file deleted")
            except OSError as e:
                logger.error(f"Failed to delete session file: {e}")

        logger.info("Logged out successfully")

    async def is_session_expired(self) -> bool:
        """Check if current session is expired or will expire soon.

        Returns:
            True if session is expired or will expire within 5 minutes, False otherwise
        """
        session = await self.get_session()
        return session is None

    async def check_and_handle_session(self) -> bool:
        """Check session validity and handle re-authentication if needed.

        Returns:
            True if session is valid, False if re-authentication is required
        """
        if not await self.is_session_expired():
            return True

        logger.warning("Session expired, re-authentication required")
        return False


# Global session manager instance
session_manager = SessionManager()
