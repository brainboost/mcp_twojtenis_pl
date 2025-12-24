# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TwojTenis MCP Server is a Python-based Model Context Protocol server that provides tools for booking badminton and tennis courts via twojtenis.pl. The service is stateless and uses PHPSESSID cookies for authentication.

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

The service is stateless - session management is handled by the client. Each MCP tool that requires authentication takes a `session_id` parameter (returned by `login()`). The server validates this PHPSESSID with each request.

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

1. **Authentication**: Login returns `session_id` (PHPSESSID) which must be passed to all protected endpoints
2. **Error Handling**: `ApiErrorException` with codes (`AUTHENTICATION_REQUIRED`, `HTTP_ERROR`, etc.)
3. **Configuration Priority**: Environment variables > config file > defaults
4. **Date Format**: DD.MM.YYYY (e.g., "24.09.2025")
5. **Time Format**: HH:MM (e.g., "10:00")

### Club IDs

Clubs have both string `id` (e.g., "blonia_sport") and numeric `num` (for API calls). The `clubs_endpoint.get_club_by_id()` handles this mapping.

Pre-configured clubs are in `config/clubs.json`.

## MCP Tool Signatures

All tools requiring authentication must receive `session_id` as the first parameter:

- `login(email, password)` -> Returns `{"success": bool, "session_id": str}`
- `get_club_schedule(session_id, club_id, sport_id, date)`
- `get_reservations(session_id)`
- `put_reservation(session_id, club_id, court_number, date, start_time, end_time, sport_id)`
- `delete_reservation(session_id, booking_id)`

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
