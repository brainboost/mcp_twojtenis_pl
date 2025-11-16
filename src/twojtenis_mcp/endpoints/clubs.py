"""Club-related MCP endpoints."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from ..client import TwojTenisClient
from ..models import Club, SportId
from ..schedule_parser import ScheduleParser

logger = logging.getLogger(__name__)


class ClubsEndpoint:
    """Endpoint for club-related operations."""

    def __init__(self):
        """Initialize clubs endpoint."""
        self.clubs_file_path = Path("config/clubs.json")
        self.sports_file_path = Path("config/sports.json")
        self._clubs_cache: list[Club] = []
        self._sports_cache: list[SportId] = []
        self._load_clubs()
        self._load_sports()
        self.client = TwojTenisClient()

    def _load_clubs(self) -> None:
        """Load clubs from json file."""
        try:
            if self.clubs_file_path.exists():
                with open(self.clubs_file_path, encoding="utf-8") as f:
                    clubs_data = json.load(f)
                self._clubs_cache = [Club(**club) for club in clubs_data]
                logger.info(f"Loaded {len(self._clubs_cache)} clubs from file")
            else:
                logger.error(f"Failed to load clubs from file: {self.clubs_file_path}")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to load clubs from file: {e}")

    def _load_sports(self) -> None:
        """Load sports from file."""
        try:
            if self.sports_file_path.exists():
                with open(self.sports_file_path, encoding="utf-8") as f:
                    sports_data = json.load(f)
                self._sports_cache = [SportId(**sport) for sport in sports_data]
                logger.info(f"Loaded {len(self._sports_cache)} sports from file")
            else:
                logger.error(
                    f"Failed to load sports from file: {self.sports_file_path}"
                )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to load sports from file: {e}")

    async def _save_cache(self):
        """Save clubs and sports cache to JSON files asynchronously."""
        try:
            # Ensure parent directories exist
            self.clubs_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.sports_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert Pydantic models to dictionaries before JSON serialization
            clubs_data = [club.model_dump() for club in self._clubs_cache]
            sports_data = [sport.model_dump() for sport in self._sports_cache]

            # Write files asynchronously
            await asyncio.to_thread(
                self._write_json_file, self.clubs_file_path, clubs_data
            )

            await asyncio.to_thread(
                self._write_json_file, self.sports_file_path, sports_data
            )

            logger.info(
                f"Successfully saved {len(self._clubs_cache)} clubs and {len(self._sports_cache)} sports to cache"
            )

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            raise

    def _write_json_file(self, file_path: Path, data: list[dict[str, Any]]) -> None:
        """Write data to JSON file with proper error handling."""
        try:
            # Create a temporary file first to ensure atomic write
            temp_path = file_path.with_suffix(".tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Replace the original file with the temporary file
            temp_path.replace(file_path)

        except Exception as e:
            logger.error(f"Failed to write JSON file {file_path}: {e}")
            # Clean up temp file if it exists
            if "temp_path" in locals() and temp_path.exists():  # type: ignore
                temp_path.unlink()  # type: ignore
            raise

    async def get_clubs(self) -> list[dict[str, Any]]:
        """Get list of all clubs.

        Returns:
            List of club dictionaries
        """
        if not self._clubs_cache:
            self._load_clubs()

        for club in self._clubs_cache:
            if club.sports is not None:
                continue
            club.sports = await self._get_club_sports(club_id=club.id)
            if club.sports is None:
                continue
            self._sports_cache.extend(club.sports)

        # Save updated cache after fetching sports
        await self._save_cache()

        return [club.model_dump() for club in self._clubs_cache]

    async def get_club_by_id(self, club_id: str) -> Club | None:
        """Get club by its club_id string"""
        if not self._clubs_cache:
            self._load_clubs()
        for club in self._clubs_cache:
            if club.id == club_id:
                return club

    async def _get_club_sports(self, club_id: str) -> list[SportId] | None:
        club_info = await self.client.with_session_retry(
            self.client.get_club_info, club_id=club_id
        )
        sports: list[SportId] = []
        info = ScheduleParser.parse_club_info(club_info)
        if info is None:
            return None
        for sport in info["sports"]:
            sports.append(SportId(id=int(sport["id"]), name=sport["name"]))
        return sports

    def get_sports(self) -> list[dict[str, Any]]:
        """Get list of all clubs.

        Returns:
            List of club dictionaries
        """
        if not self._sports_cache:
            self._load_sports()

        return [sport.model_dump() for sport in self._sports_cache]

    def validate_sport_id(self, sport_id: int) -> bool:
        """Check if a sport ID is valid and supported.

        Args:
            sport_id: Sport identifier to validate

        Returns:
            True if the sport ID is valid and supported, False otherwise
        """
        try:
            if not isinstance(sport_id, int) or sport_id <= 0:
                return False
            for sport in self._sports_cache:
                if sport_id == sport.id:
                    return True
            return False
        except Exception:
            return False


# Global clubs endpoint instance
clubs_endpoint = ClubsEndpoint()
