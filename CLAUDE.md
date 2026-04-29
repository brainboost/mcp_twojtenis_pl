# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TwojTenis MCP Server is a Python-based Model Context Protocol server that provides tools for booking badminton and tennis courts via twojtenis.pl. Authentication uses Auth0 OIDC (Authorization Code + PKCE) to obtain JWTs for the new API.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the server (STDIO mode)
uv run -m twojtenis_mcp.server

# Run with debug mode (for VSCode debugging)
uv run python -m twojtenis_mcp.server --debug -Xfrozen_modules=off

# Test with MCP Inspector
npx @modelcontextprotocol/inspector uv run -m twojtenis_mcp.server

# Run tests
uv run pytest tests/

# Run a single test
uv run pytest tests/test_specific_file.py::test_function_name

# Lint code
uvx ruff check src/
```

## Architecture

### Stateless Service Design

The service is stateless. Authentication is via Auth0 — `login_oauth` drives a headless browser to obtain JWT tokens. Booking tools are pending migration to the new Auth0-backed API.

### Layer Structure

```
server.py           # FastMCP server with @mcp.tool() decorators (MCP layer)
├── endpoints/      # Business logic layer
│   ├── clubs.py       # Club data management
│   ├── reservations.py # Booking operations, login
│   └── schedules.py    # Schedule parsing and availability
├── client.py        # HTTP client wrapper (API layer)
├── models.py        # Pydantic models for type safety
├── config.py        # Configuration with env var priority
└── utils.py         # Utility functions
```

### Key Design Patterns

1. **Authentication**: `login_oauth` returns `{access_token, refresh_token, expires_at, ...}` JWT for `api.twojetenis.pl`
2. **Error Handling**: `ApiErrorException` with codes (`AUTHENTICATION_REQUIRED`, `HTTP_ERROR`, etc.)
3. **Configuration Priority**: Environment variables > config file > defaults
4. **Date Format**: DD.MM.YYYY (e.g., "24.09.2025")
5. **Time Format**: HH:MM (e.g., "10:00")

### Club IDs

Clubs have both string `id` (e.g., "blonia_sport") and numeric `num` (for API calls). The `clubs_endpoint.get_club_by_id()` handles this mapping.

Pre-configured clubs are in `config/clubs.json`.

## MCP Tool Signatures

Authentication (Auth0):

- `login_oauth(email, password)` → Returns `{"success": bool, "access_token": str, "refresh_token": str|None, "expires_at": int, ...}`
- `refresh_oauth_token(refresh_token)` → Returns same shape as `login_oauth`

Booking tools (pending migration to Auth0; currently use a legacy session parameter):

- `get_club_schedule(session_id, club_id, sport_id, date)`
- `get_reservations(session_id)`
- `put_reservation(session_id, club_id, court_number, date, start_time, end_time, sport_id)`
- `delete_reservation(session_id, booking_id)`

## Auth0

`login_oauth` returns `{access_token, refresh_token, expires_at, ...}` JWT for `api.twojetenis.pl`. Refresh via `refresh_oauth_token` (pure HTTP, no browser).

Auth0 params (do **not** "fix" the typo in audience):

| Param        | Value                                       |
|--------------|---------------------------------------------|
| Domain       | `twojtenis.eu.auth0.com`                    |
| Client ID    | `86BsGMVf8imqTkuKVkxeW2FalNALsO4y`          |
| Audience     | `https://api.twojetenis.pl` ← extra `e`     |
| Redirect URI | `https://app.twojtenis.pl`                  |
| Flow         | Authorization Code + PKCE (S256, no secret) |

ROPC is disabled on this tenant; login requires headless Chromium via Playwright.

To enable browser auth:

```bash
uv pip install -e ".[browser-auth]"
uv run playwright install chromium
```

New error codes: `OAUTH_INVALID_CREDENTIALS`, `OAUTH_PLAYWRIGHT_REQUIRED`, `OAUTH_BROWSER_TIMEOUT`, `OAUTH_NETWORK_ERROR`, `OAUTH_UNEXPECTED`.

## Debugging in VSCode

To debug the MCP server:

1. Add to `.vscode/launch.json`:
```json
{
  "configurations": [{
    "name": "Attach to Running MCP Server",
    "type": "debugpy",
    "request": "attach",
    "connect": {"host": "localhost", "port": 5678},
    "pathMappings": [{"localRoot": "${workspaceFolder}", "remoteRoot": "."}]
  }]
}
```

2. Run with `--debug` flag and attach debugger to port 5678
