"""Configuration management for TwojTenis MCP server."""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager with environment variables and file fallback."""

    def __init__(self, config_path: str | None = None):
        """Initialize configuration.

        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path or os.getenv(
            "TWOJTENIS_CONFIG_PATH", "config/config.json"
        )
        self._config_data: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file if it exists."""
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    self._config_data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Warning: Failed to load config file {self.config_path}: {e}")
                self._config_data = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with priority: env vars > config file > default.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value
        """
        # First check environment variables
        env_value = os.getenv(key.upper())
        if env_value is not None:
            return env_value

        # Then check config file
        if key in self._config_data:
            return self._config_data[key]

        # Return default
        return default

    @property
    def email(self) -> str:
        """Get user email from configuration."""
        email = self.get("TWOJTENIS_EMAIL")
        if not email:
            raise ValueError(
                "TWOJTENIS_EMAIL is required in environment variables or config file"
            )
        return email

    @property
    def password(self) -> str:
        """Get user password from configuration."""
        password = self.get("TWOJTENIS_PASSWORD")
        if not password:
            raise ValueError(
                "TWOJTENIS_PASSWORD is required in environment variables or config file"
            )
        return password

    @property
    def base_url(self) -> str:
        """Get base URL for twojtenis.pl."""
        return self.get("TWOJTENIS_BASE_URL", "https://www.twojtenis.pl")

    @property
    def session_lifetime(self) -> int:
        """Get session lifetime in minutes."""
        return int(self.get("TWOJTENIS_SESSION_LIFETIME", "120"))

    @property
    def request_timeout(self) -> int:
        """Get HTTP request timeout in seconds."""
        return int(self.get("TWOJTENIS_REQUEST_TIMEOUT", "30"))

    @property
    def retry_attempts(self) -> int:
        """Get number of retry attempts for failed requests."""
        return int(self.get("TWOJTENIS_RETRY_ATTEMPTS", "3"))

    @property
    def retry_delay(self) -> float:
        """Get delay between retry attempts in seconds."""
        return float(self.get("TWOJTENIS_RETRY_DELAY", "1.0"))

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "email": self.email,
            "base_url": self.base_url,
            "session_lifetime": self.session_lifetime,
            "request_timeout": self.request_timeout,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
        }


# Global configuration instance
config = Config()
