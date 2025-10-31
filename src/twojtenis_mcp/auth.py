"""Authentication and session management for TwojTenis MCP server."""

import json
import logging
from datetime import datetime
from pathlib import Path

from .client import TwojTenisClient
from .config import config
from .models import UserSession

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user authentication and session persistence."""

    def __init__(self):
        """Initialize session manager."""
        self.client = TwojTenisClient()
        self._session: UserSession | None = None
        self._session_file_path = Path(config.session_file_path)
        self._session_file_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize session manager and restore or create session.

        Returns:
            True if session is successfully initialized, False otherwise
        """
        # Try to load existing session
        if await self._load_session():
            logger.info("Existing session loaded successfully")
            return True
        else:
            logger.info("No existing session found, attempting new login")
            # Create new session
            session = await self._create_new_session()
            return session is not None

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

            # Convert string dates back to datetime objects if present
            if "expires_at" in session_data and session_data["expires_at"]:
                session_data["expires_at"] = datetime.fromisoformat(
                    session_data["expires_at"]
                )
            else:
                session_data["expires_at"] = None

            self._session = UserSession(**session_data)
            logger.info(f"Session loaded from file: {self._session.phpsessid[:8]}...")
            return True

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load session from file: {e}")
            return False

    async def _save_session(self) -> None:
        """Save current session to file."""
        if not self._session:
            return

        try:
            session_data = self._session.model_dump()
            # Convert datetime to string for JSON serialization if present
            if self._session.expires_at:
                session_data["expires_at"] = self._session.expires_at.isoformat()

            with open(self._session_file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Session saved to file: {self._session.phpsessid[:8]}...")

        except (OSError, TypeError) as e:
            logger.error(f"Failed to save session to file: {e}")


    async def _create_new_session(self) -> UserSession | None:
        """Create new session by logging in.

        Returns:
            UserSession if created successfully, None otherwise
        """
        try:
            phpsessid = await self.client.login(config.email, config.password)
            if phpsessid:
                self._session = UserSession(
                    phpsessid=phpsessid,
                    expires_at=None,  # No expiration needed with new approach
                    is_active=True,
                    email=config.email,
                )
                await self._save_session()
                logger.info(f"New session created: {phpsessid[:8]}...")
                return self._session
            else:
                logger.error("Failed to create new session")
                return None

        except Exception as e:
            logger.error(f"Error creating new session: {e}")
            return None


    async def get_session(self) -> UserSession | None:
        """Get current active session.

        Returns:
            Current session if active, None otherwise
        """
        if not self._session or not self._session.is_active:
            await self._create_new_session()

        return self._session

    async def refresh_session(self) -> UserSession | None:
        """Force refresh session by creating a new one.

        Returns:
            New session if created successfully, None otherwise
        """
        logger.info("Forcing session refresh due to server error")
        return await self._create_new_session()

    def get_phpsessid(self) -> str | None:
        """Get PHPSESSID for API calls.

        Returns:
            PHPSESSID if session is active, None otherwise
        """
        if self._session and self._session.is_active:
            return self._session.phpsessid
        return None

    async def logout(self) -> None:
        """Logout and invalidate current session."""
        if self._session:
            self._session.is_active = False
            await self._save_session()
            self._session = None

        # Delete session file
        if self._session_file_path.exists():
            try:
                self._session_file_path.unlink()
                logger.info("Session file deleted")
            except OSError as e:
                logger.error(f"Failed to delete session file: {e}")

        logger.info("Logged out successfully")

    async def change_credentials(self, email: str, password: str) -> bool:
        """Change user credentials and create new session.

        Args:
            email: New email address
            password: New password

        Returns:
            True if credentials were changed successfully, False otherwise
        """
        # Logout current session
        await self.logout()

        # Temporarily update config for login
        old_email = config.email
        old_password = config.password

        try:
            # Temporarily override config values
            config._config_data["TWOJTENIS_EMAIL"] = email
            config._config_data["TWOJTENIS_PASSWORD"] = password

            # Create new session with new credentials
            success = await self._create_new_session()

            if success:
                logger.info("Credentials changed successfully")
                return True
            else:
                # Restore old credentials on failure
                config._config_data["TWOJTENIS_EMAIL"] = old_email
                config._config_data["TWOJTENIS_PASSWORD"] = old_password
                logger.error("Failed to change credentials")
                return False

        except Exception as e:
            # Restore old credentials on error
            config._config_data["TWOJTENIS_EMAIL"] = old_email
            config._config_data["TWOJTENIS_PASSWORD"] = old_password
            logger.error(f"Error changing credentials: {e}")
            return False


# Global session manager instance
session_manager = SessionManager()
