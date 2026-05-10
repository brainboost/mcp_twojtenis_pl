"""Shared pytest fixtures for TwojTenis MCP tests."""

import os

import pytest


@pytest.fixture(autouse=True)
def required_env_vars(monkeypatch):
    """Set required env vars so tests don't need a real .env file."""
    monkeypatch.setenv("TWOJTENIS_MAIN_API_URL", "https://app-twojtenis-api-p-weu.azurewebsites.net")
    monkeypatch.setenv("AUTH0_CLIENT_ID", "test-client-id")
