"""Combined server supporting both STDIO and SSE modes."""

import argparse
import asyncio
import logging

from .server import initialize as mcp_initialize
from .server import main as mcp_main
from .sse_server import run_sse_server, run_sse_server_async

logger = logging.getLogger(__name__)


async def run_combined_server(
    mode: str = "stdio", sse_host: str = "0.0.0.0", sse_port: int = 8000
) -> None:
    """Run the server in the specified mode.

    Args:
        mode: Server mode ("stdio", "sse", or "both")
        sse_host: Host for SSE server
        sse_port: Port for SSE server
    """
    logger.info(f"Starting TwojTenis MCP Server in {mode} mode")

    if mode == "stdio":
        # Run only STDIO MCP server
        logger.info("Running in STDIO mode only")
        await mcp_initialize()
        mcp_main()

    elif mode == "sse":
        # Run only SSE server
        logger.info(f"Running in SSE mode on {sse_host}:{sse_port}")
        run_sse_server(sse_host, sse_port)

    elif mode == "both":
        # Run both servers concurrently
        logger.info(f"Running in both modes - STDIO + SSE on {sse_host}:{sse_port}")

        # Start SSE server in background
        sse_task = await run_sse_server_async(sse_host, sse_port)

        try:
            # Run MCP server in foreground
            await mcp_initialize()
            mcp_main()
        except KeyboardInterrupt:
            logger.info("Shutting down servers...")
        finally:
            # Cancel SSE server task
            sse_task.cancel()
            try:
                await sse_task
            except asyncio.CancelledError:
                pass

    else:
        logger.error(f"Unknown mode: {mode}")
        raise ValueError(f"Mode must be 'stdio', 'sse', or 'both', got: {mode}")


def main() -> None:
    """Main entry point for combined server."""
    parser = argparse.ArgumentParser(description="TwojTenis MCP Server")
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse", "both"],
        default="stdio",
        help="Server mode: stdio (MCP), sse (HTTP), or both",
    )
    parser.add_argument(
        "--sse-host", default="0.0.0.0", help="Host for SSE server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--sse-port", type=int, default=8000, help="Port for SSE server (default: 8000)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run server
    try:
        asyncio.run(
            run_combined_server(
                mode=args.mode, sse_host=args.sse_host, sse_port=args.sse_port
            )
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
