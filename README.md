# TwojTenis MCP Server

An MCP (Model Context Protocol) server for booking badminton and tennis courts via **app.twojtenis.pl**. Authentication uses Auth0 OIDC; every booking call hits the new Azure-hosted JSON API with a `Bearer <jwt>` header.

## Features

- **Auth0 login** — Authorization Code + PKCE via headless Chromium; returns JWT access + refresh tokens.
- **Club catalog** — list clubs, fetch details, view booking settings (max-days-in-advance, cancel windows).
- **Schedule** — public bookings + excludes for any date, no auth needed.
- **Reservations** — list/create/cancel; bulk-create multiple courts in one server-side call.
- **Stateless** — no sessions stored server-side; the MCP caller supplies the `access_token` per call.
- **Typed** — Pydantic v2 models for the new API.

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
git clone <repository-url>
cd twojtenis_pl
uv sync
uv pip install -e ".[browser-auth]"
uv run playwright install chromium
```

The `browser-auth` extra installs Playwright; required because Auth0 ROPC is disabled on this tenant and login goes through the Universal Login form.

## Configuration

All configuration is via environment variables — there is no config file in 0.2.0.

```bash
# Optional — overrides for dev/staging
TWOJTENIS_MAIN_API_URL=https://app-twojtenis-api-p-weu.azurewebsites.net
TWOJTENIS_REQUEST_TIMEOUT=30

# Auth0 — see "Auth0 Client ID" note below before filling these in
AUTH0_DOMAIN=twojtenis.eu.auth0.com
AUTH0_CLIENT_ID=<your-auth0-client-id>
AUTH0_AUDIENCE=https://api.twojetenis.pl   # extra 'e' is intentional
AUTH0_REDIRECT_URI=https://app.twojtenis.pl
AUTH0_SCOPE=openid profile email offline_access
AUTH0_BROWSER_HEADLESS=true
AUTH0_BROWSER_TIMEOUT=60
AUTH0_BROWSER_EXECUTABLE_PATH=  # set on AWS Lambda
```

### Auth0 Client ID

`AUTH0_CLIENT_ID` is the OAuth 2.0 client registration ID for the **twojtenis.pl** application on `twojtenis.eu.auth0.com`. This is a public identifier (PKCE flow — no client secret involved).

To find the value:
1. Open the [Auth0 dashboard](https://manage.auth0.com/) for the `twojtenis.eu.auth0.com` tenant.
2. Go to **Applications** → find the twojtenis.pl app → copy the **Client ID**.

If you are a twojtenis.pl user (not the tenant admin), ask the project maintainer for the client ID, or extract it from the browser's network traffic when visiting `app.twojtenis.pl` (it appears in the Auth0 `/authorize` redirect URL as `client_id=...`).

## Usage

### Running the Server

```bash
uv run -m twojtenis_mcp.server
```

### Available Tools (v0.2.0)

Authentication:

| Tool | Args | Returns |
|------|------|---------|
| `login_oauth` | `email`, `password` | `{success, access_token, refresh_token, expires_at, token_type, scope, id_token}` |
| `refresh_oauth_token` | `refresh_token` | same shape as `login_oauth` |

Booking — every tool takes `access_token` as the first arg:

| Tool | Args | Returns |
|------|------|---------|
| `get_all_clubs` | `access_token` | `[{id, name, address, openHours, priceMin, priceMax, ...}]` |
| `get_club_locations` | `access_token, club_id, sport=""` | `[{id, name, sport, short_name, tags, sort_number, type, has_light, ...}]` — courts at the club. `sport` is derived: `tennis`, `badminton`, `padel`, `squash`, `table_tennis`, `fitness`, `bowling`, `football`, `multi`, or `null`. Pass `sport="badminton"` etc. to filter. |
| `get_club_schedule` | `access_token, club_id, date` | `{success, data: {club_id, date, availability: [{location_id, location_name, sport, slots: [{start, end, available}]}]}}` — 30-min slots over the club's open hours, marked available iff no booking/exclude overlaps. |
| `get_reservations` | `access_token, from_date="", to_date=""` | list of bookings (default window: today..+90d) |
| `get_reservation_details` | `access_token, booking_id` | `{success, reservation}` or `{success: False, message}` |
| `put_reservation` | `access_token, club_id, location_id, location_name, date, start_time, end_time` | `{success, reservation}` |
| `put_bulk_reservation` | `access_token, club_id, court_bookings` | `{success, reservations: [...]}` |
| `delete_reservation` | `access_token, booking_id` | `{success, message}` |
| `delete_all_reservations` | `access_token` | `{success, deleted_count, deleted_booking_ids, errors}` |

Date format: `YYYY-MM-DD` or legacy `DD.MM.YYYY` (both accepted on input).
Time format: `HH:MM` or `HH:MM:SS`.
IDs (clubs, locations, bookings, players) are UUIDs.

#### Bulk reservation

`court_bookings` is a list of dicts:

```json
[
  {"location_id": "3931aabd-...", "location_name": "Badminton 2",
   "date": "2026-05-11", "start_time": "16:00", "end_time": "17:00"},
  {"location_id": "3931aabd-...", "location_name": "Badminton 2",
   "date": "2026-05-11", "start_time": "17:00", "end_time": "18:00"}
]
```

The server makes one `calculate-price` call per item, then a single `POST /bookings` with all entries.

## Auth0 Authentication

`login_oauth` drives Auth0 Universal Login via headless Chromium and exchanges the resulting authorization code for JWT tokens. Refresh via `refresh_oauth_token` (pure HTTP, no browser).

If `playwright` is not installed, `login_oauth` returns `{success: false, code: "OAUTH_PLAYWRIGHT_REQUIRED"}`.

For AWS Lambda, set `AUTH0_BROWSER_EXECUTABLE_PATH=/opt/chromium/chromium` and use the [Sparticuz/chromium](https://github.com/Sparticuz/chromium) layer.

OAuth error codes: `OAUTH_INVALID_CREDENTIALS`, `OAUTH_PLAYWRIGHT_REQUIRED`, `OAUTH_BROWSER_TIMEOUT`, `OAUTH_NETWORK_ERROR`, `OAUTH_UNEXPECTED`.

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run -m twojtenis_mcp.server
```

Open the URL printed in the console (e.g. `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...`).

Example call:

```json
{
  "tool": "get_club_schedule",
  "arguments": {
    "access_token": "<jwt from login_oauth>",
    "club_id": "958662f0-0bd2-4fdc-8bef-bb2d69761adb",
    "date": "2026-05-11"
  }
}
```

### Debugging in VSCode

1. Add `.vscode/launch.json`:

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

2. Run with `--debug` and attach the debugger to port 5678:

```bash
npx @modelcontextprotocol/inspector uv run python -m twojtenis_mcp.server --debug -Xfrozen_modules=off
```

## Migration from 0.1.x

Breaking changes:

- `session_id` (PHPSESSID) → `access_token` (Auth0 JWT) on every tool.
- Club ids are UUIDs (e.g. `958662f0-0bd2-4fdc-8bef-bb2d69761adb`); legacy string ids and numeric `num` are gone.
- Courts addressed by `location_id` (UUID) + `location_name` instead of numeric `court_number`.
- `sport_id` removed (new API isn't sport-scoped — filter client-side via `location_id`).
- `get_all_sports` removed.
- Removed env vars: `TWOJTENIS_EMAIL`, `TWOJTENIS_PASSWORD`, `TWOJTENIS_BASE_URL`, `TWOJTENIS_RETRY_ATTEMPTS`, `TWOJTENIS_RETRY_DELAY`, `TWOJTENIS_CONFIG_PATH`, `TWOJTENIS_CLUBS_FILE`.

## Development

### Project Structure

```
src/twojtenis_mcp/
├── __init__.py
├── server.py           # FastMCP entrypoint + @mcp.tool() definitions
├── config.py           # Env-driven configuration
├── client.py           # ApiClient — async httpx, Bearer auth, JSON only
├── tech_group.py       # Per-club regional API URL resolver (cached)
├── locations.py        # Court UUID + name resolver
├── models.py           # Pydantic v2 models for the new API
├── utils.py            # Date conversion, auth0 sub URL encoding
├── jwt_utils.py        # JWT decode helpers (sub, expiry)
├── oauth_browser.py    # Playwright-driven Auth0 login flow
├── oauth_client.py     # PKCE + token exchange
└── endpoints/
    ├── clubs.py
    ├── reservations.py
    ├── schedules.py
    └── oauth.py
```

### Tests

```bash
uv run pytest tests/
```

Real-API integration tests (`test_real_login_returns_jwt_with_correct_audience`) auto-skip unless `TWOJTENIS_EMAIL` and `TWOJTENIS_PASSWORD` are set.

### Lint

```bash
uvx ruff check src/
```

## Error Handling

All booking tools wrap `ApiErrorException` and return `{success: false, code, message, details}` on failure.

Codes: `AUTHENTICATION_REQUIRED`, `FORBIDDEN`, `HTTP_ERROR`, `REQUEST_FAILED`, `VALIDATION_ERROR`, `NO_TECH_GROUP`, `PRICE_CALCULATION_FAILED`, `BOOKING_FAILED`.

## License

MIT
