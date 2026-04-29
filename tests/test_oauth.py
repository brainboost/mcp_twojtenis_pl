"""Tests for OAuth authentication functionality."""

import base64
import hashlib
import os
import sys
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from twojtenis_mcp.models import ApiErrorException

# ---------------------------------------------------------------------------
# Test 1: PKCE pair validation
# ---------------------------------------------------------------------------


def test_pkce_pair_is_valid_s256():
    """Verifier is 43-char URL-safe base64; challenge is base64url(sha256(verifier))."""
    import re

    from twojtenis_mcp.oauth_client import OAuthClient

    verifier, challenge = OAuthClient._pkce_pair()

    # verifier must match URL-safe base64 chars, 43-128 chars
    assert re.match(r"^[A-Za-z0-9_\-]{43,128}$", verifier), f"Bad verifier: {verifier}"

    # challenge must equal base64url(sha256(verifier_bytes)).rstrip('=')
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert challenge == expected_challenge, (
        f"Challenge mismatch: {challenge!r} != {expected_challenge!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: login drives browser then exchanges code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_drives_browser_then_exchanges_code(mocker):
    """Mock browser + httpx POST; verify correct kwargs and expires_at calculation."""
    from twojtenis_mcp.oauth_client import OAuthClient

    fixed_code = "test_auth_code_abc123"
    fake_tokens = {
        "access_token": "eyJhbGciOiJSUzI1NiJ9.fake.token",
        "refresh_token": "v1.refresh.token",
        "id_token": "eyJhbGciOiJSUzI1NiJ9.fake.id",
        "expires_in": 86400,
        "token_type": "Bearer",
        "scope": "openid profile email offline_access",
    }

    mock_browser = mocker.patch(
        "twojtenis_mcp.oauth_client.perform_browser_login",
        new=mocker.AsyncMock(return_value=fixed_code),
    )

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_tokens

    mock_post = mocker.AsyncMock(return_value=mock_response)
    mocker.patch("httpx.AsyncClient.post", mock_post)

    client = OAuthClient()
    before = int(time.time())
    result = await client.login(email="test@example.com", password="secret")

    # Browser was called exactly once with the required kwargs
    mock_browser.assert_called_once()
    call_kwargs = mock_browser.call_args.kwargs
    assert call_kwargs["email"] == "test@example.com"
    assert call_kwargs["password"] == "secret"
    assert "code_challenge" in call_kwargs
    assert "state" in call_kwargs

    # Token exchange POSTed with correct grant type and no client_secret
    mock_post.assert_called_once()
    post_call = mock_post.call_args
    posted_data = (
        post_call.kwargs.get("data") or post_call.args[1] if post_call.args else {}
    )
    if not posted_data:
        posted_data = post_call.kwargs.get("data", {})
    assert posted_data.get("grant_type") == "authorization_code"
    assert posted_data.get("code") == fixed_code
    assert "client_secret" not in posted_data

    # expires_at is within 5 seconds of expected
    expected_expires = before + fake_tokens["expires_in"]
    assert abs(result["expires_at"] - expected_expires) <= 5
    assert result["access_token"] == fake_tokens["access_token"]
    assert result["refresh_token"] == fake_tokens["refresh_token"]


# ---------------------------------------------------------------------------
# Test 3: invalid credentials from browser raises OAUTH_INVALID_CREDENTIALS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_raises_invalid_credentials_when_browser_says_so(mocker):
    """OAuthBrowserError with kind='invalid_credentials' → OAUTH_INVALID_CREDENTIALS."""
    from twojtenis_mcp.oauth_browser import OAuthBrowserError
    from twojtenis_mcp.oauth_client import OAuthClient

    mocker.patch(
        "twojtenis_mcp.oauth_client.perform_browser_login",
        side_effect=OAuthBrowserError("Wrong password", kind="invalid_credentials"),
    )
    mock_post = mocker.AsyncMock()
    mocker.patch("httpx.AsyncClient.post", mock_post)

    client = OAuthClient()
    with pytest.raises(ApiErrorException) as exc_info:
        await client.login(email="bad@example.com", password="wrong")

    assert exc_info.value.code == "OAUTH_INVALID_CREDENTIALS"
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: browser timeout raises OAUTH_BROWSER_TIMEOUT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_raises_browser_timeout_when_browser_times_out(mocker):
    """OAuthBrowserError with kind='timeout' → OAUTH_BROWSER_TIMEOUT."""
    from twojtenis_mcp.oauth_browser import OAuthBrowserError
    from twojtenis_mcp.oauth_client import OAuthClient

    mocker.patch(
        "twojtenis_mcp.oauth_client.perform_browser_login",
        side_effect=OAuthBrowserError("Timed out waiting for redirect", kind="timeout"),
    )

    client = OAuthClient()
    with pytest.raises(ApiErrorException) as exc_info:
        await client.login(email="user@example.com", password="pass")

    assert exc_info.value.code == "OAUTH_BROWSER_TIMEOUT"


# ---------------------------------------------------------------------------
# Test 5: missing playwright raises OAUTH_PLAYWRIGHT_REQUIRED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_raises_playwright_required_when_module_missing(mocker):
    """ImportError from oauth_browser import → OAUTH_PLAYWRIGHT_REQUIRED."""
    from twojtenis_mcp.oauth_client import OAuthClient

    mocker.patch(
        "twojtenis_mcp.oauth_client.perform_browser_login",
        side_effect=ImportError("No module named 'playwright'"),
    )

    client = OAuthClient()
    with pytest.raises(ApiErrorException) as exc_info:
        await client.login(email="user@example.com", password="pass")

    assert exc_info.value.code == "OAUTH_PLAYWRIGHT_REQUIRED"


# ---------------------------------------------------------------------------
# Test 6: refresh returns new tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(mocker):
    """Refresh POSTs correct body and returns parsed tokens with expires_at."""
    from twojtenis_mcp.oauth_client import OAuthClient

    fake_tokens = {
        "access_token": "new.access.token",
        "refresh_token": "new.refresh.token",
        "id_token": None,
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "openid profile email offline_access",
    }

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_tokens

    mock_post = mocker.AsyncMock(return_value=mock_response)
    mocker.patch("httpx.AsyncClient.post", mock_post)

    client = OAuthClient()
    before = int(time.time())
    result = await client.refresh(refresh_token="old.refresh.token")

    mock_post.assert_called_once()
    post_call = mock_post.call_args
    posted_data = post_call.kwargs.get("data", {})
    assert posted_data.get("grant_type") == "refresh_token"
    assert posted_data.get("refresh_token") == "old.refresh.token"
    assert "client_id" in posted_data

    expected_expires = before + fake_tokens["expires_in"]
    assert abs(result["expires_at"] - expected_expires) <= 5
    assert result["access_token"] == "new.access.token"


# ---------------------------------------------------------------------------
# Test 7: refresh with invalid_grant raises OAUTH_INVALID_CREDENTIALS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_raises_invalid_credentials_on_invalid_grant(mocker):
    """403 response with error=invalid_grant → OAUTH_INVALID_CREDENTIALS."""
    from twojtenis_mcp.oauth_client import OAuthClient

    mock_response = mocker.MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {
        "error": "invalid_grant",
        "error_description": "Refresh token expired",
    }

    mock_post = mocker.AsyncMock(return_value=mock_response)
    mocker.patch("httpx.AsyncClient.post", mock_post)

    client = OAuthClient()
    with pytest.raises(ApiErrorException) as exc_info:
        await client.refresh(refresh_token="expired.token")

    assert exc_info.value.code == "OAUTH_INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# Test 8: login_oauth tool returns success dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_oauth_tool_returns_success_dict(mocker):
    """login_oauth tool wraps endpoint result in {"success": True, ...}."""
    from twojtenis_mcp import server

    fake_result = {
        "access_token": "tok.abc",
        "refresh_token": "ref.abc",
        "expires_at": int(time.time()) + 3600,
        "token_type": "Bearer",
        "scope": "openid profile email offline_access",
        "id_token": "id.abc",
    }

    mocker.patch.object(
        server.oauth_endpoint,
        "login",
        new=mocker.AsyncMock(return_value=fake_result),
    )

    result = await server.login_oauth.fn(email="user@example.com", password="pass")

    assert result["success"] is True
    assert result["access_token"] == "tok.abc"
    assert result["refresh_token"] == "ref.abc"


# ---------------------------------------------------------------------------
# Test 9: login_oauth tool returns error dict on ApiErrorException
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_oauth_tool_returns_error_dict_on_exception(mocker):
    """login_oauth tool catches ApiErrorException and returns {"success": False, ...}."""
    from twojtenis_mcp import server

    mocker.patch.object(
        server.oauth_endpoint,
        "login",
        new=mocker.AsyncMock(
            side_effect=ApiErrorException(
                code="OAUTH_INVALID_CREDENTIALS",
                message="Invalid credentials",
            )
        ),
    )

    result = await server.login_oauth.fn(email="bad@example.com", password="wrong")

    assert result["success"] is False
    assert result["code"] == "OAUTH_INVALID_CREDENTIALS"
    assert "Invalid credentials" in result["message"]


# ---------------------------------------------------------------------------
# Test 10: Integration test (env-gated)
# ---------------------------------------------------------------------------


# @pytest.mark.skipif(
#     not all(os.getenv(k) for k in ("TWOJTENIS_EMAIL", "TWOJTENIS_PASSWORD")),
#     reason="needs real credentials and 'browser-auth' extras installed",
# )
@pytest.mark.asyncio
async def test_real_login_returns_jwt_with_correct_audience():
    """Real Auth0 login; decodes JWT and verifies aud/iss/exp claims."""
    import jwt

    from twojtenis_mcp.oauth_client import OAuthClient

    client = OAuthClient()
    result = await client.login(
        email=os.environ["TWOJTENIS_EMAIL"],
        password=os.environ["TWOJTENIS_PASSWORD"],
    )

    access_token = result["access_token"]

    # Must be exactly three dot-separated base64 segments
    parts = access_token.split(".")
    assert len(parts) == 3, f"Expected JWT with 3 parts, got {len(parts)}"

    payload = jwt.decode(
        access_token,
        options={"verify_signature": False},
        algorithms=["RS256"],
    )

    aud = payload["aud"]
    aud_list = [aud] if isinstance(aud, str) else aud
    assert "https://api.twojetenis.pl" in aud_list, f"Wrong audience: {aud}"
    assert payload["iss"] == "https://twojtenis.eu.auth0.com/", (
        f"Wrong issuer: {payload['iss']}"
    )
    assert payload["exp"] > int(time.time()), "Token already expired"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
