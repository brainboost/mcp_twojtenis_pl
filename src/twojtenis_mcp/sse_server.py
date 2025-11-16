"""SSE (Server-Sent Events) support for remote mode."""

import asyncio
import json
import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse

from .server import mcp

logger = logging.getLogger(__name__)


class SSEManager:
    """Manages SSE connections and events."""

    def __init__(self):
        """Initialize SSE manager."""
        self.connections: set[asyncio.Queue] = set()
        self.app = FastAPI(title="TwojTenis MCP SSE Server")
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "TwojTenis.pl MCP SSE Server",
                "version": "0.1.0",
                "endpoints": {"sse": "/events", "health": "/health", "tools": "/tools"},
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "connections": len(self.connections)}

        @self.app.get("/events")
        async def events(request: Request):
            """SSE endpoint for real-time events."""

            async def event_generator():
                """Generate SSE events."""
                queue = asyncio.Queue()
                self.connections.add(queue)

                try:
                    # Send initial connection event
                    await queue.put(
                        {
                            "type": "connected",
                            "data": {
                                "message": "Connected to TwojTenis MCP SSE Server"
                            },
                        }
                    )

                    # Keep connection alive and send events
                    while True:
                        try:
                            # Wait for event with timeout
                            event = await asyncio.wait_for(queue.get(), timeout=30.0)

                            # Send event
                            yield {
                                "event": event.get("type", "message"),
                                "data": json.dumps(event.get("data", {})),
                            }

                        except TimeoutError:
                            # Send keep-alive ping
                            yield {
                                "event": "ping",
                                "data": json.dumps({"timestamp": "now"}),
                            }

                except Exception as e:
                    logger.error(f"Error in SSE event generator: {e}")
                finally:
                    self.connections.remove(queue)

            return EventSourceResponse(event_generator())

        @self.app.post("/tools/{tool_name}")
        async def execute_tool(tool_name: str, request: Request):
            """Execute MCP tool via HTTP POST."""
            try:
                # Get request body
                body = await request.json()
                params = body.get("params", {})

                # Find the tool function
                tool_func = None
                for tool in mcp.tools:  # type: ignore
                    if tool.name == tool_name:
                        tool_func = tool.function
                        break

                if not tool_func:
                    return {
                        "success": False,
                        "message": f"Tool '{tool_name}' not found",
                    }

                # Execute the tool
                try:
                    result = await tool_func(**params)

                    # Broadcast result to all connected clients
                    await self.broadcast(
                        {
                            "type": "tool_result",
                            "data": {
                                "tool": tool_name,
                                "params": params,
                                "result": result,
                            },
                        }
                    )

                    return {"success": True, "result": result}

                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    return {
                        "success": False,
                        "message": f"Error executing tool: {str(e)}",
                    }

            except Exception as e:
                logger.error(f"Error in tool endpoint: {e}")
                return {"success": False, "message": f"Request error: {str(e)}"}

        @self.app.get("/tools")
        async def list_tools():
            """List available tools."""
            tools = []
            for tool in mcp.tools:  # type: ignore
                tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.schema.get("properties", {})
                        if tool.schema
                        else {},
                    }
                )

            return {"tools": tools}

    async def broadcast(self, event: dict[str, Any]):
        """Broadcast event to all connected clients.

        Args:
            event: Event to broadcast
        """
        if not self.connections:
            return

        # Create a copy of connections to avoid modification during iteration
        connections = self.connections.copy()

        for queue in connections:
            try:
                await queue.put(event)
            except Exception as e:
                logger.warning(f"Failed to send event to connection: {e}")
                # Remove broken connection
                self.connections.discard(queue)

    async def send_session_update(self, session_status: str, details: dict[str, Any]):
        """Send session status update to all clients.

        Args:
            session_status: Session status (e.g., "authenticated", "expired", "refreshed")
            details: Additional details about the session
        """
        await self.broadcast(
            {
                "type": "session_update",
                "data": {
                    "status": session_status,
                    "details": details,
                    "timestamp": "now",
                },
            }
        )

    async def send_reservation_update(self, action: str, reservation: dict[str, Any]):
        """Send reservation update to all clients.

        Args:
            action: Action type (e.g., "created", "deleted", "modified")
            reservation: Reservation details
        """
        await self.broadcast(
            {
                "type": "reservation_update",
                "data": {
                    "action": action,
                    "reservation": reservation,
                    "timestamp": "now",
                },
            }
        )

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the SSE server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        logger.info(f"Starting SSE server on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port, log_level="info")


class SSEIntegration:
    """Integration between MCP server and SSE functionality."""

    def __init__(self, sse_manager: SSEManager):
        """Initialize SSE integration.

        Args:
            sse_manager: SSE manager instance
        """
        self.sse_manager = sse_manager
        self._setup_mcp_hooks()

    def _setup_mcp_hooks(self):
        """Setup hooks to broadcast MCP events."""
        # This would require modifying the MCP server to emit events
        # For now, we'll provide methods that can be called manually
        pass

    async def notify_tool_execution(
        self, tool_name: str, params: dict[str, Any], result: Any
    ):
        """Notify about tool execution.

        Args:
            tool_name: Name of the executed tool
            params: Tool parameters
            result: Tool execution result
        """
        await self.sse_manager.broadcast(
            {
                "type": "tool_executed",
                "data": {
                    "tool": tool_name,
                    "params": params,
                    "result": result,
                    "timestamp": "now",
                },
            }
        )


# Global SSE manager instance
sse_manager = SSEManager()
sse_integration = SSEIntegration(sse_manager)


def run_sse_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the SSE server in blocking mode.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    sse_manager.run(host, port)


async def run_sse_server_async(host: str = "0.0.0.0", port: int = 8000) -> asyncio.Task:
    """Run the SSE server in non-blocking mode.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    config = uvicorn.Config(sse_manager.app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    # Run in background task
    task = asyncio.create_task(server.serve())
    return task
