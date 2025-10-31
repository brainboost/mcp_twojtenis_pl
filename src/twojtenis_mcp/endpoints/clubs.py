"""Club-related MCP endpoints."""

import json
import logging
from pathlib import Path
from typing import Any

from ..models import Club

logger = logging.getLogger(__name__)


class ClubsEndpoint:
    """Endpoint for club-related operations."""

    def __init__(self):
        """Initialize clubs endpoint."""
        self.clubs_file_path = Path("config/clubs.json")
        self._clubs_cache: list[Club] = []
        self._load_clubs()

    def _load_clubs(self) -> None:
        """Load clubs from file or create from CSV data."""
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

    def get_clubs(self) -> list[dict[str, Any]]:
        """Get list of all clubs.

        Returns:
            List of club dictionaries
        """
        if not self._clubs_cache:
            self._load_clubs()

        return [club.model_dump() for club in self._clubs_cache]

    def get_club_by_id(self, club_id: str) -> dict[str, Any]:
        """Get club by ID.

        Args:
            club_id: Club identifier

        Returns:
            Club dictionary if found, empty dict otherwise
        """
        if not self._clubs_cache:
            self._load_clubs()

        for club in self._clubs_cache:
            if club.id == club_id:
                return club.model_dump()

        return {}


# Global clubs endpoint instance
clubs_endpoint = ClubsEndpoint()
