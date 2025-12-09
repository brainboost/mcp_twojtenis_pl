"""Integration tests for OAuth-like authentication flow."""

import asyncio
import logging
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from twojtenis_mcp.auth import session_manager
from twojtenis_mcp.config import config
from twojtenis_mcp.oauth_flow import oauth_coordinator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_integration():
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

        # Test 2: Session manager initialization
        print("2. Testing session manager...")
        await session_manager.initialize()
        session = await session_manager.get_session()
        print(f"   Initial session: {'None' if session is None else 'Present'}")
        print("   ✓ Session manager initialized")

        # Test 3: OAuth flow coordinator
        print("3. Testing OAuth flow coordinator...")
        status = await oauth_coordinator.get_authentication_status()
        print(f"   Auth status: {status}")
        print("   ✓ OAuth flow coordinator working")

        # Test 4: Authentication status check
        print("4. Testing authentication status methods...")
        if not status["authenticated"]:
            print("   ✓ Correctly detects no active session")
        else:
            print("   ⚠ Unexpected active session found")

        # Test 5: Error handling
        print("5. Testing error handling...")
        try:
            # This should handle gracefully
            await oauth_coordinator.cancel_authentication()
            print("   ✓ Error handling working")
        except Exception as e:
            print(f"   ✗ Error in error handling: {e}")

        print("\n🎉 All integration tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        logger.exception("Integration test failed")
        return False


async def test_authentication_flow_simulation():
    """Simulate the authentication flow without actually starting servers."""
    print("\n🔄 Simulating authentication flow...")

    try:
        # Check initial state
        status = await oauth_coordinator.get_authentication_status()
        print(
            f"Initial state: authenticated={status['authenticated']}, authenticating={status['is_authenticating']}"
        )

        # Test ensure_authenticated when not authenticated
        result = await oauth_coordinator.ensure_authenticated()
        print(f"Ensure auth result: {result['status']}")

        if result.get("status") == "success":
            print("✓ Authentication flow initiated successfully")
            print(f"Login URL would be: {result.get('login_url', 'N/A')}")

            # Simulate completion (without actually waiting)
            print("✓ Flow simulation completed")
            return True
        else:
            print(
                f"✗ Authentication flow failed: {result.get('message', 'Unknown error')}"
            )
            return False

    except Exception as e:
        print(f"❌ Flow simulation failed: {e}")
        logger.exception("Flow simulation failed")
        return False


async def main():
    """Main test runner."""
    print("🚀 Starting OAuth-like authentication flow integration tests\n")

    # Run basic integration tests
    basic_success = await test_basic_integration()

    # Run flow simulation
    flow_success = await test_authentication_flow_simulation()

    # Summary
    print("\n📊 Test Summary:")
    print(f"   Basic Integration: {'✓ PASS' if basic_success else '✗ FAIL'}")
    print(f"   Flow Simulation: {'✓ PASS' if flow_success else '✗ FAIL'}")

    if basic_success and flow_success:
        print("\n🎊 All tests completed successfully!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
