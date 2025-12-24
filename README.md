# TwojTenis MCP Server

An MCP (Model Context Protocol) server for booking badminton and tennis courts via the twojtenis.pl website. This server provides a standardized interface for interacting with the court booking system, supporting both local (STDIO) and remote (SSE) communication modes.

## Features

- **Authentication**: Secure login with session management
- **Club Information**: Get list of available clubs
- **Schedule Management**: View court availability schedules
- **Reservation Management**: Book, view, and cancel court reservations
- **Session Persistence**: Automatic session refresh and recovery
- **Error Handling**: Robust error handling with retry logic
- **Typed Entities**: Full type safety with Pydantic models
- **SSE Support**: Real-time updates via Server-Sent Events
- **Dual Mode**: Support for both STDIO and HTTP/SSE modes

## Installation

### Prerequisites

- Python 3.11 or higher
- `uv` for dependency management

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd twojtenis_pl
```

2. Install dependencies using `uv`:
```bash
uv sync
```

3. Set up configuration:
```bash
cp .env.example .env
# Edit .env with your TwojTenis.pl credentials
```

## Configuration

The server supports configuration through environment variables and/or a configuration file. Environment variables take precedence over the configuration file.

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Required
TWOJTENIS_EMAIL=your_email@example.com
TWOJTENIS_PASSWORD=your_password

# Optional
TWOJTENIS_CONFIG_PATH=config/config.json
TWOJTENIS_CLUBS_FILE=config/clubs.json
TWOJTENIS_BASE_URL=https://www.twojtenis.pl
TWOJTENIS_SESSION_LIFETIME=120  # minutes
TWOJTENIS_REQUEST_TIMEOUT=30    
TWOJTENIS_RETRY_ATTEMPTS=3
TWOJTENIS_RETRY_DELAY=1.0
```

### Configuration File

Alternatively, create `config/config.json`:

```json
{
  "TWOJTENIS_EMAIL": "your_email@example.com",
  "TWOJTENIS_PASSWORD": "your_password",
  "TWOJTENIS_SESSION_REFRESH": 60,
  "TWOJTENIS_SESSION_LIFETIME": 120
}
```

## Usage

### Running the Server

Start the MCP server:

```bash
uv run -m twojtenis_mcp.server
```

### Available Tools

The server provides the following MCP tools:

 **get_all_clubs()** - Get list of all available clubs
 **get_all_sports()** - Get list of all supported sport IDs
 **get_club_schedule(club_id, sport_id, date)** - Get court availability schedule
 **get_reservations()** - Get user's current reservations
 **put_reservation(club_id, court_number, date, hour, sport_id)** - Make a single reservation
 **put_bulk_reservation(club_id, sport_id, court_bookings)** - Make multiple reservations in one request
 **delete_reservation(club_id, court_number, date, hour)** - Delete a reservation
 **check_availability(club_id, sport_id, court_number, date, hour)** - Check court availability
 **get_available_slots(club_id, sport_id, date, court_number)** - Get all available slots

#### Bulk Reservation

The `put_bulk_reservation` tool allows booking multiple courts in a single API call. Each booking is a dictionary with the following fields:

- `court`: Court number as string (e.g., "1", "2", "3")
- `date`: Date in DD.MM.YYYY format (e.g., "27.12.2025")
- `time_start`: Start time in HH:MM format (e.g., "21:00")
- `time_end`: End time in HH:MM format (e.g., "21:30")

Example:
```json
{
  "club_id": "blonia_sport",
  "sport_id": 84,
  "court_bookings": [
    {"court": "1", "date": "27.12.2025", "time_start": "21:00", "time_end": "21:30"},
    {"court": "2", "date": "27.12.2025", "time_start": "21:00", "time_end": "21:30"}
  ]
}
```


### Testing with MCP Inspector

To test the MCP tools functionality:

1. Run the MCP Inspector:
```bash
npx @modelcontextprotocol/inspector uv run -m twojtenis_mcp.server
```

2. Open the MCP Inspector Web UI:
In the console with running step 1 command, find the link URL 
http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...  and open it in a browser 

4. Connect the Inspector to your MCP server and test the tools

Example test case in MCP Inspector:
```json
{
  "tool": "get_club_schedule",
  "arguments": {
    "club_id": "blonia_sport",
    "sport_id": 84,
    "date": "28.10.2025"
  }
}
```

### Debugging with MCP Inspector in VSCode

Ensure you have Python Debugger extension installed in VSCode. Put the following json into the .vscode/launch.json file:
```json
{
  "configurations": [
    {
      "name": "Attach to Running MCP Server",
      "type": "debugpy",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "."
        }
      ]
    }
  ]
}
```

1. Run the MCP Inspector with debug mode command:
```bash
npx @modelcontextprotocol/inspector uv run python -m twojtenis_mcp.server --debug -Xfrozen_modules=off
```

2. Open the URL in the console output in the browser

3. Connect the Inspector to your MCP server with button Connect

4. In the VSCode, open the server.py and set breakpoints on the methods you want to debug. 

5. Start debugging session clicking on the top triangle button with dropdown, choosing "Python Debugger: Debug using launch.json" and then "Attach to Running MCP Server". Debug session will start in VSCode.

### Date/Time Formats

- **Date**: DD.MM.YYYY (e.g., "24.09.2025")
- **Time**: HH:MM (e.g., "10:00", "10:30")

### Club IDs

Common club IDs include:
- `blonia_sport` - Błonia Sport
- `ks_nadwislan_krakow` - KS Nadwiślan Kraków
- `krakowska_szkola_tenisa_tenis24` - Krakowska Szkoła Tenisa TENIS24
- `forehand_krakowska_szkola_tenisa` - Forehand Krakowska Akademia Tenisa
- `katenis__korty_olsza` - KATenis - korty Olsza
- `korty_dabskie` - Korty Dąbskie
- `wks_wawel` - WKS Wawel
- `klub_tenisowy_blonia_krakow` - Klub Tenisowy Błonia Kraków

## Examples

### Basic Usage

```python
# Login
await login("user@example.com", "password")

# Get clubs
clubs = await get_clubs()

# Get schedule for badminton at Błonia Sport
schedule = await get_club_schedule(
    club_id="blonia_sport",
    sport_id=84,  # Badminton
    date="24.09.2025"
)

# Check availability
availability = await check_availability(
    club_id="blonia_sport",
    sport_id=84,
    court_number=1,
    date="24.09.2025",
    hour="10:00"
)

# Make a reservation
result = await put_reservation(
    club_id="blonia_sport",
    court_number=1,
    date="24.09.2025",
    hour="10:00",
    sport_id=84
)
```

### Session Management

The server automatically manages sessions:
- Sessions are stored in `config/session.json`
- Sessions are refreshed every 60 seconds by default
- Session lifetime is 120 minutes
- Automatic re-authentication on session expiry

## Development

### Project Structure

```
src/twojtenis_mcp/
├── __init__.py
├── server.py              # Main MCP server
├── config.py              # Configuration management
├── auth.py                # Authentication and session management
├── client.py              # HTTP client wrapper
├── models.py              # Typed data models
├── schedule_parser.py     # Schedule parsing logic
├── utils.py               # Utility functions
└── endpoints/             # MCP tool implementations
    ├── __init__.py
    ├── clubs.py
    ├── reservations.py
    └── booking.py
```

### Running Tests

```bash
uv run pytest tests/
```

MCP Inspedtor allows you to debug and test server. Run from project folder in terminal:

```bash
npx @modelcontextprotocol/inspector uv run python -m twojtenis_mcp.server
```

### Code Formatting

```bash
uvx ruff check src/
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Check your email and password in the configuration
2. **Session Expired**: The server will automatically re-authenticate
3. **Network Errors**: Check your internet connection and the TwojTenis.pl website status
4. **Invalid Date/Time**: Ensure dates are in DD.MM.YYYY format and times in HH:MM format

### Logging

The server provides detailed logging. Check the console output for error messages and debugging information.

### Session Issues

If you encounter session issues:
1. Delete `config/session.json`
2. Restart the server

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Create an issue in the repository

## API Reference

### Authentication

The server uses PHPSESSID cookies for authentication. Sessions are automatically managed and refreshed.

### Error Handling

All tools return standardized responses with:
- `success`: Boolean indicating success/failure
- `message`: Descriptive message
- `data`: Response data (for successful operations)
- `timestamp`: ISO timestamp of the response

### Rate Limiting

The server implements retry logic with exponential backoff for failed requests. Default configuration:
- 3 retry attempts
- 1.0 second base delay
- Exponential backoff multiplier

### Data Models

The server uses Pydantic models for type safety:
- `Club`: Club information
- `Court`: Court availability
- `Schedule`: Club schedule
- `Reservation`: User reservation
- `UserSession`: Session information