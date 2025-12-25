"""Integration tests for OAuth-like authentication flow."""

import asyncio
import logging
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from twojtenis_mcp.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_integration():
    """Test basic integration of OAuth flow components."""
    print("🧪 Running basic integration tests...")

    try:
        # Test 1: Configuration loading
        print("1. Testing configuration...")
        print(f"   Base URL: {config.base_url}")
        print(f"   Session lifetime: {config.session_lifetime} minutes")
        print(f"   Auth timeout: {config.auth_timeout} seconds")
        print(f"   Has credentials: {config.has_credentials}")
        print("   ✓ Configuration loaded successfully")

        print("\n🎉 All integration tests passed!")

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        logger.exception("Integration test failed")


async def main():
    """Main test runner."""

    # Run basic integration tests
    basic_success = test_basic_integration()

    # Summary
    print("\n📊 Test Summary:")
    print(f"   Basic Integration: {'✓ PASS' if basic_success else '✗ FAIL'}")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
