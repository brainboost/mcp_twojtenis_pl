import asyncio

from src.twojtenis_mcp.auth import SessionManager
from twojtenis_mcp.client import TwojTenisClient

session_manager = SessionManager()

asyncio.run(session_manager.initialize())
sess = asyncio.run(session_manager.get_session())
client = TwojTenisClient()
club_info = asyncio.run(
    client.with_session_retry(client.get_club_info, club_id="blonia_sport")
)

print(club_info)
