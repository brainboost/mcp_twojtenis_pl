# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TwojTenis MCP Server is a Python-based Model Context Protocol server that provides tools for booking badminton and tennis courts via **app.twojtenis.pl**. Authentication uses Auth0 OIDC (Authorization Code + PKCE) to obtain JWTs that are used as `Authorization: Bearer <token>` against two Azure-hosted JSON APIs.

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

The server is stateless. Each MCP tool call is fully authenticated by an Auth0 `access_token` JWT supplied by the caller (obtained from `login_oauth`). No tokens, sessions, or state are persisted server-side.

### Two API hosts

- **Main API** (`https://app-twojtenis-api-p-weu.azurewebsites.net`): clubs, regions, players, prices.
- **Regional / technical-group API** (e.g. `https://app-twojtenis-tech-krakow-api-p-weu.azurewebsites.net`): bookings, schedule, excludes. Each club declares its own tech-group host via `GET /api/v1/Clubs/{id}/technical-group`. `TechGroupResolver` caches that lookup per process.

### Layer Structure

```
server.py           # FastMCP server with @mcp.tool() decorators (MCP layer)
├── endpoints/      # Business logic
│   ├── clubs.py        # /api/v1/Clubs (list, by id, details, settings)
│   ├── reservations.py # /bookings/my, calculate-price, POST /bookings, cancel
│   ├── schedules.py    # /bookings/public + /excludes/public
│   └── oauth.py        # Auth0 login + refresh
├── client.py        # ApiClient: thin async httpx wrapper, Bearer auth
├── tech_group.py    # Per-club regional service URL resolver (cached)
├── locations.py     # Court UUID + name resolver
├── models.py        # Pydantic v2 models for new API
├── config.py        # Env-driven configuration
├── utils.py         # Date conversion, auth0 sub URL encoding
├── jwt_utils.py     # JWT decode helpers (sub, expiry)
├── oauth_browser.py # Playwright-driven Auth0 Universal Login flow
└── oauth_client.py  # PKCE + token exchange
```

### Key Design Patterns

1. **Authentication**: `login_oauth(email, password)` returns `{access_token, refresh_token, expires_at, ...}`. Every booking tool takes that `access_token` and sends `Authorization: Bearer <token>`.
2. **Error Handling**: `ApiErrorException(code, message, details)`. Tool wrappers convert it to `{success: False, code, message, details}`.
3. **Configuration**: env vars only — `TWOJTENIS_MAIN_API_URL`, `TWOJTENIS_REQUEST_TIMEOUT`, all `AUTH0_*`.
4. **Date Format**: ISO `YYYY-MM-DD` is canonical. Tools accept either ISO or legacy `DD.MM.YYYY`; `utils.to_iso_date` normalizes.
5. **Time Format**: `HH:MM` from callers; the API expects `HH:MM:SS` and the endpoint layer normalizes.
6. **Identifiers**: clubs and courts (locations) are UUIDs. Booker IDs are looked up per-club via `/Clubs/{id}/players/{auth0|sub}`.

## MCP Tool Signatures (v0.2.0)

Authentication (Auth0):

- `login_oauth(email, password)` → `{success, access_token, refresh_token, expires_at, token_type, scope, id_token}`
- `refresh_oauth_token(refresh_token)` → same shape as `login_oauth`

Booking tools (all take an Auth0 `access_token` from `login_oauth`):

- `get_all_clubs(access_token)` — list clubs (UUID id, name, address, openHours, prices, ...)
- `get_club_locations(access_token, club_id)` — list courts at one club; returns `id` (UUID, used as `location_id`) and `name` (used as `location_name`) plus `short_name`, `tags`, `sort_number`, `type`, `has_light`, `is_enabled`, `group_name`. Source: the `locations` field of `GET /api/v1/Clubs/{id}`.
- `get_club_schedule(access_token, club_id, date)` — public bookings + excludes for one day
- `get_reservations(access_token, from_date="", to_date="")` — defaults to `today .. today+90d`
- `get_reservation_details(access_token, booking_id)`
- `put_reservation(access_token, club_id, location_id, location_name, date, start_time, end_time)`
- `put_bulk_reservation(access_token, club_id, court_bookings)` — one server-side POST with N items
- `delete_reservation(access_token, booking_id)`
- `delete_all_reservations(access_token)`

Removed in 0.2.0: `get_all_sports` (no equivalent in new API), `sport_id` parameter (the new schedule is not sport-scoped — filter client-side by `location_id`), legacy `session_id` param.

## Auth0

`login_oauth` returns a JWT signed by `twojtenis.eu.auth0.com` with `aud: https://api.twojetenis.pl`. Refresh via `refresh_oauth_token` (pure HTTP, no browser).

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

OAuth error codes: `OAUTH_INVALID_CREDENTIALS`, `OAUTH_PLAYWRIGHT_REQUIRED`, `OAUTH_BROWSER_TIMEOUT`, `OAUTH_NETWORK_ERROR`, `OAUTH_UNEXPECTED`.
Booking error codes: `AUTHENTICATION_REQUIRED`, `FORBIDDEN`, `HTTP_ERROR`, `REQUEST_FAILED`, `VALIDATION_ERROR`, `NO_TECH_GROUP`, `PRICE_CALCULATION_FAILED`, `BOOKING_FAILED`.

## Migration Notes (0.1.x → 0.2.0)

Breaking changes for downstream MCP clients:

- `session_id` (PHPSESSID) is gone everywhere — every booking tool now takes `access_token` (an Auth0 JWT).
- Club ids are UUIDs (e.g. `958662f0-0bd2-4fdc-8bef-bb2d69761adb`); the legacy string ids (`blonia_sport`) and numeric `num` no longer exist.
- Courts are addressed by `location_id` (UUID) and `location_name` (display string), replacing the old numeric `court_number`.
- `sport_id` is removed from `get_club_schedule` and `put_reservation`. The new API isn't sport-scoped; filter client-side via `location_id` from `get_club_schedule`.
- `get_all_sports` is removed.
- Date format prefers ISO `YYYY-MM-DD`; `DD.MM.YYYY` still accepted on input for backwards-compat with existing prompts.

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
