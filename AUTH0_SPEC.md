# Auth0 Authentication for twojtenis_mcp

> **Branch:** `auth0` | **Worktree:** `D:\Projects\mcp\twojtenis_pl.auth0`
> **Goal:** Add Auth0 (OIDC, Authorization Code + PKCE) authentication so the
> MCP server can obtain a JWT for `https://api.twojetenis.pl` (the new HTTP
> API used by `app.twojtenis.pl`) on the user's behalf.

---

## Why this exists

The current server authenticates against the **legacy** site
`https://old.twojtenis.pl` via PHPSESSID
(`TwojTenisClient.login()` in `src/twojtenis_mcp/client.py`). The site's
modern SPA at `app.twojtenis.pl` uses Auth0 with `@auth0/auth0-react` v2.2.4,
talking to a JSON API at `api.twojetenis.pl`. This spec adds the second auth
path; it does **not** remove or change the existing PHPSESSID flow.

After this work lands:

- A new MCP tool `login_oauth(email, password)` returns
  `{success, access_token, refresh_token, expires_at, ...}`.
- A new tool `refresh_oauth_token(refresh_token)` returns a refreshed token
  set without re-prompting credentials.
- The existing `login` tool, all PHPSESSID-based tools, and all current
  endpoints continue to work unchanged.

Migrating individual endpoints from old → new API is **out of scope**.

---

## Auth0 parameters (verified from a captured `/authorize` request)

| Parameter      | Value                                          |
|----------------|------------------------------------------------|
| Domain         | `twojtenis.eu.auth0.com`                       |
| Client ID      | `86BsGMVf8imqTkuKVkxeW2FalNALsO4y`             |
| Audience       | `https://api.twojetenis.pl`                    |
| Redirect URI   | `https://app.twojtenis.pl`                     |
| Scope          | `openid profile email offline_access`          |
| Flow           | Authorization Code + PKCE (S256, no secret)    |

> **Typo warning — do not "fix" it.** The audience is `api.twojetenis.pl`
> (extra `e`), not `api.twojtenis.pl`. The site's production config has the
> typo. Sending the corrected spelling returns an opaque token instead of
> a JWT and the API rejects it.

> **The captured SPA request did not include `offline_access`** — it relies
> on Auth0's silent-auth iframe. We add `offline_access` so the MCP server
> can refresh without re-prompting credentials. If the API's "Allow Offline
> Access" toggle is off in the Auth0 dashboard, the response will simply
> omit `refresh_token`. Code must handle that case (caller re-runs login on
> expiry).

> **ROPC was tested and confirmed disabled** for this client. Verified
> response: `{"error":"unauthorized_client","error_description":"Grant type
> 'password' not allowed for the client."}`. We go straight to
> Authorization Code + PKCE driven by Playwright. No fallback needed.

---

## Strategy: Authorization Code + PKCE via Playwright

Drive the actual Universal Login form. The flow:

1. Generate PKCE pair (`verifier`, `challenge`), `state` and `nonce`
   (random URL-safe).
2. Launch headless Chromium, navigate to
   `https://twojtenis.eu.auth0.com/authorize?...` with all the params from
   the table above plus the PKCE/state/nonce values.
3. Auth0's New Universal Login renders. Fill `input[name="username"]` and
   `input[name="password"]`, click the submit button.
4. The form posts; Auth0 redirects through `/login/callback` and finally
   to `redirect_uri` (`https://app.twojtenis.pl`) with `?code=...&state=...`.
5. Intercept the navigation to `redirect_uri` before the SPA loads — grab
   `code`, verify `state`, close the browser.
6. POST to `/oauth/token`:

```python
{
  "grant_type": "authorization_code",
  "client_id": CLIENT_ID,
  "code": "<intercepted>",
  "code_verifier": "<our_pkce_verifier>",
  "redirect_uri": REDIRECT_URI
}
```

7. Response contains `access_token` (JWT), `refresh_token` (if
   `offline_access` is honored), `id_token`, `expires_in`, `scope`,
   `token_type`.

### Why Playwright and not just `httpx`

You can't simulate the login form with bare HTTP because:

- Auth0 New Universal Login renders the form via JS, the actual POST target
  varies, anti-bot middleware checks browser fingerprints, and CSRF tokens
  are embedded in the page.
- Replicating those internals against a tenant we don't control means our
  code breaks every time Auth0 ships a Universal Login update.
- A real browser is the supported escape hatch — slower per-call but stable.

Refresh token usage stays pure HTTP — only initial login needs the browser.

---

## Files to create

### `src/twojtenis_mcp/oauth_client.py`

```python
class OAuthClient:
    """Handles Auth0 token acquisition for api.twojetenis.pl."""

    def __init__(self) -> None: ...

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Drive the Auth0 Universal Login form via Playwright and exchange
        the resulting authorization code for tokens.

        Returns:
            {
              "access_token": "<jwt>",
              "refresh_token": "<token>" | None,
              "expires_at": <epoch_seconds>,
              "token_type": "Bearer",
              "scope": "openid profile email offline_access",
              "id_token": "<jwt>" | None,
            }

        Raises:
            ApiErrorException with codes:
                OAUTH_INVALID_CREDENTIALS  - login form rejected creds
                OAUTH_PLAYWRIGHT_REQUIRED  - playwright not installed
                OAUTH_BROWSER_TIMEOUT      - flow exceeded timeout
                OAUTH_NETWORK_ERROR        - connection issue with Auth0
                OAUTH_UNEXPECTED           - everything else
        """

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """POST grant_type=refresh_token. Same return shape as login().
        Pure HTTP — no browser involved.
        """

    @staticmethod
    def _pkce_pair() -> tuple[str, str]:
        """Returns (verifier, challenge) for PKCE S256.
        verifier: 43-char URL-safe base64 (32 random bytes encoded).
        challenge: base64url(sha256(verifier)).rstrip('=')
        """

    @staticmethod
    def _random_state() -> str:
        """16-byte URL-safe random string."""

    async def _exchange_code(
        self,
        code: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        """POST to /oauth/token with grant_type=authorization_code.
        Returns the token dict with expires_at computed from expires_in."""
```

Implementation notes:

- Use `httpx.AsyncClient` for the token exchange and refresh — match the
  style in `client.py`.
- `expires_at = int(time.time()) + response["expires_in"]`. Don't parse the
  JWT to determine expiry; trust the server.
- All Auth0 endpoint URLs use the new `config.auth0_*` properties so the
  domain is overridable for tests.
- Honor `config.request_timeout`.
- Lazy-import the browser module: `from .oauth_browser import perform_browser_login`
  inside `login()`, wrapped in try/except `ImportError` → raise
  `OAUTH_PLAYWRIGHT_REQUIRED`.

### `src/twojtenis_mcp/oauth_browser.py`

```python
"""Playwright-driven Auth0 Universal Login. Lazy-imported by oauth_client.py
so users don't pay the dependency cost unless login() is actually called."""

async def perform_browser_login(
    *,
    domain: str,
    client_id: str,
    audience: str,
    redirect_uri: str,
    scope: str,
    code_challenge: str,
    state: str,
    nonce: str,
    email: str,
    password: str,
    headless: bool = True,
    timeout_s: int = 60,
) -> str:
    """Drive the login form, intercept the redirect, return the auth code.

    Returns the `code` query param from the redirect URL.

    Raises:
        OAuthBrowserError(message, kind) where kind is:
            'invalid_credentials' - explicit login rejection text appeared
            'timeout'             - redirect didn't fire within timeout_s
            'unexpected'          - anything else
    """
```

Critical details for the implementation:

- Build authorize URL with `urllib.parse.urlencode` — never f-string-format
  user-controlled values into URLs.
- Register the request interception **before** navigating to authorize URL
  (timing-sensitive; the redirect can happen during initial auth if Auth0
  has a session cookie). Use `page.on("request", ...)` and check
  `request.url.startswith(redirect_uri)`.
- Selector strategy with fallbacks:
  ```python
  await page.fill('input[name="username"], input[name="email"], input[type="email"]', email)
  await page.fill('input[name="password"], input[type="password"]', password)
  await page.click('button[type="submit"], button[name="action"][value="default"]')
  ```
- Detect invalid credentials: after submit, before timeout, check for the
  error banner. Auth0 New Universal Login uses
  `[role="alert"]` or class `ulp-alert-error`. Race it against the
  redirect interception — whichever wins decides the outcome.
- Always `await context.close()` and `await browser.close()` in a `finally`.
- On timeout, capture `page.screenshot()` to a temp file and include the
  path in the exception message — invaluable for debugging.
- **Do not log the password.** Log only that login was attempted.

### `src/twojtenis_mcp/endpoints/oauth.py`

```python
from typing import Any

from ..oauth_client import OAuthClient


class OAuthEndpoint:
    def __init__(self) -> None:
        self.client = OAuthClient()

    async def login(self, email: str, password: str) -> dict[str, Any]:
        return await self.client.login(email, password)

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        return await self.client.refresh(refresh_token)


oauth_endpoint = OAuthEndpoint()
```

### `tests/test_oauth.py`

See **Tests** section below.

---

## Files to modify

### `src/twojtenis_mcp/config.py`

Add properties (env vars override; defaults match production values):

```python
@property
def auth0_domain(self) -> str:
    return self.get("AUTH0_DOMAIN", "twojtenis.eu.auth0.com")

@property
def auth0_client_id(self) -> str:
    return self.get("AUTH0_CLIENT_ID", "86BsGMVf8imqTkuKVkxeW2FalNALsO4y")

@property
def auth0_audience(self) -> str:
    # Note: production typo is intentional (api.twojetenis.pl, extra 'e')
    return self.get("AUTH0_AUDIENCE", "https://api.twojetenis.pl")

@property
def auth0_redirect_uri(self) -> str:
    return self.get("AUTH0_REDIRECT_URI", "https://app.twojtenis.pl")

@property
def auth0_scope(self) -> str:
    return self.get("AUTH0_SCOPE", "openid profile email offline_access")

@property
def auth0_browser_headless(self) -> bool:
    return self.get("AUTH0_BROWSER_HEADLESS", "true").lower() == "true"

@property
def auth0_browser_timeout(self) -> int:
    return int(self.get("AUTH0_BROWSER_TIMEOUT", "60"))
```

Append the new keys to `to_dict()`.

### `src/twojtenis_mcp/server.py`

Add two tools after the existing `login` tool. Add the import next to other
endpoint imports:

```python
from .endpoints.oauth import oauth_endpoint
```

```python
@mcp.tool()
async def login_oauth(email: str, password: str) -> dict[str, Any]:
    """Authenticate with Auth0 to obtain a JWT for api.twojetenis.pl.

    Use this for the new JSON API. For legacy old.twojtenis.pl, use `login`.
    First call launches a headless browser to drive the Auth0 login form;
    subsequent token renewals via `refresh_oauth_token` are pure HTTP.

    Returns:
        On success:
            {
              "success": True,
              "access_token": "<jwt>",
              "refresh_token": "<token>" | None,
              "expires_at": <epoch_seconds>,
              "token_type": "Bearer",
              "scope": "openid profile email offline_access",
              "id_token": "<jwt>" | None,
            }
        On failure:
            {"success": False, "message": "...", "code": "..."}
    """
    try:
        tokens = await oauth_endpoint.login(email=email, password=password)
        logger.debug(f"OAuth login succeeded for {email}")
        return {"success": True, **tokens}
    except ApiErrorException as e:
        logger.error(f"OAuth login failed for {email}: {e.code} {e.message}")
        return {"success": False, "message": e.message, "code": e.code}
    except Exception as e:
        logger.error(f"OAuth login unexpected error for {email}: {e}")
        return {"success": False, "message": f"Login failed: {e}"}


@mcp.tool()
async def refresh_oauth_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an Auth0 access token using a refresh token.

    Returns the same shape as login_oauth on success. Does not launch a
    browser — pure HTTP.
    """
    try:
        tokens = await oauth_endpoint.refresh(refresh_token)
        return {"success": True, **tokens}
    except ApiErrorException as e:
        logger.error(f"OAuth refresh failed: {e.code} {e.message}")
        return {"success": False, "message": e.message, "code": e.code}
    except Exception as e:
        logger.error(f"OAuth refresh unexpected error: {e}")
        return {"success": False, "message": f"Refresh failed: {e}"}
```

### `src/twojtenis_mcp/models.py`

No code change. New `ApiErrorException` codes used:

- `OAUTH_INVALID_CREDENTIALS` — Auth0 form rejected credentials
- `OAUTH_PLAYWRIGHT_REQUIRED` — `playwright` not installed
- `OAUTH_BROWSER_TIMEOUT` — login flow exceeded `auth0_browser_timeout`
- `OAUTH_NETWORK_ERROR` — connection issue talking to Auth0
- `OAUTH_UNEXPECTED` — anything else

### `pyproject.toml`

Add to runtime dependencies (only `pyjwt` for token decoding in tests/utils):

```toml
"pyjwt>=2.8.0",
```

Add an optional group for the browser fallback (not in default install):

```toml
[project.optional-dependencies]
browser-auth = ["playwright>=1.40"]
```

### `.env.example`

Append:

```bash
# Auth0 settings (defaults are production values; override only for tests/dev)
# AUTH0_DOMAIN=twojtenis.eu.auth0.com
# AUTH0_CLIENT_ID=86BsGMVf8imqTkuKVkxeW2FalNALsO4y
# AUTH0_AUDIENCE=https://api.twojetenis.pl
# AUTH0_REDIRECT_URI=https://app.twojtenis.pl
# AUTH0_SCOPE=openid profile email offline_access

# Set to 'false' to watch the browser drive the login (debugging only)
# AUTH0_BROWSER_HEADLESS=true
# AUTH0_BROWSER_TIMEOUT=60
```

### `README.md`

Add a section after the existing setup docs:

```markdown
## Auth0 (new API)

Two parallel auth paths exist:

- **Legacy**: `login(email, password) → session_id` (PHPSESSID), used by all
  existing endpoints, talks to `old.twojtenis.pl`.
- **New**: `login_oauth(email, password) → {access_token, refresh_token, ...}`,
  intended for `api.twojetenis.pl`. Refresh via `refresh_oauth_token` (pure
  HTTP, no browser).

The first `login_oauth` call drives Auth0's Universal Login form via
headless Chromium because the tenant disallows the password grant. To enable:

    uv pip install -e ".[browser-auth]"
    uv run playwright install chromium

If `playwright` is not installed, `login_oauth` raises with code
`OAUTH_PLAYWRIGHT_REQUIRED`.
```

### `CLAUDE.md`

Append a short section mirroring the README addition (developer-focused).

---

## Tests (TDD — write these first)

`tests/test_oauth.py` — mirrors `tests/test_bulk_reservation.py` style
(sys.path injection, pytest-asyncio, pytest-mock). All unit tests mock both
`httpx` and the browser module so they run offline and fast.

### Unit tests (no network, no browser)

1. **`test_pkce_pair_is_valid_s256`** — verifier matches `[A-Za-z0-9_-]{43,128}`,
   challenge equals `base64url(sha256(verifier_bytes)).rstrip('=')`.

2. **`test_login_drives_browser_then_exchanges_code`** — mock
   `oauth_browser.perform_browser_login` to return a fixed code. Mock
   `httpx.AsyncClient.post` to return 200 with full token response.
   Assert:
   - `perform_browser_login` called exactly once with the right kwargs
   - `_exchange_code` POSTs `grant_type=authorization_code` with the code,
     verifier, client_id, redirect_uri (no client_secret)
   - Returned dict has `expires_at ≈ now + expires_in` (within 5 sec)

3. **`test_login_raises_invalid_credentials_when_browser_says_so`** — mock
   `perform_browser_login` to raise `OAuthBrowserError(kind="invalid_credentials")`.
   Assert `ApiErrorException(code="OAUTH_INVALID_CREDENTIALS")` raised,
   token endpoint not called.

4. **`test_login_raises_browser_timeout_when_browser_times_out`** — mock
   `perform_browser_login` to raise `OAuthBrowserError(kind="timeout")`.
   Assert `ApiErrorException(code="OAUTH_BROWSER_TIMEOUT")` raised.

5. **`test_login_raises_playwright_required_when_module_missing`** —
   monkeypatch `importlib` so `from .oauth_browser import ...` raises
   `ImportError`. Assert `ApiErrorException(code="OAUTH_PLAYWRIGHT_REQUIRED")`.

6. **`test_refresh_returns_new_tokens`** — mock POST to `/oauth/token`.
   Assert request body keys: `grant_type=refresh_token`, `client_id`,
   `refresh_token`. Assert response parsed correctly with computed `expires_at`.

7. **`test_refresh_raises_invalid_credentials_on_invalid_grant`** — mock
   refresh response 403 with `{"error": "invalid_grant"}`. Assert
   `ApiErrorException(code="OAUTH_INVALID_CREDENTIALS")`.

8. **`test_login_oauth_tool_returns_success_dict`** — mock
   `oauth_endpoint.login`. Call the tool function directly. Assert
   `{"success": True, "access_token": ...}`.

9. **`test_login_oauth_tool_returns_error_dict_on_exception`** — mock
   `oauth_endpoint.login` to raise `ApiErrorException`. Assert
   `{"success": False, "message": ..., "code": "..."}`.

### Integration test (env-gated, skipped without credentials)

10. **`test_real_login_returns_jwt_with_correct_audience`** — only runs when
    `TWOJTENIS_EMAIL` and `TWOJTENIS_PASSWORD` env vars are set.
    Calls real `OAuthClient().login()`. Decodes JWT *without verification*
    (`jwt.decode(token, options={"verify_signature": False})`).
    Asserts:
    - `aud` claim equals `"https://api.twojetenis.pl"` (with the typo)
    - `iss` claim equals `"https://twojtenis.eu.auth0.com/"`
    - `exp` claim is in the future
    - Token is exactly three dot-separated base64 segments

    Mark with:
    ```python
    @pytest.mark.skipif(
        not all(os.getenv(k) for k in ("TWOJTENIS_EMAIL", "TWOJTENIS_PASSWORD")),
        reason="needs real credentials and 'browser-auth' extras installed",
    )
    ```

---

## Acceptance criteria

1. All unit tests in `tests/test_oauth.py` pass:
   `uv run pytest tests/test_oauth.py -v`
2. Existing test suite still passes (no regressions):
   `uv run pytest tests/`
3. With real credentials in `.env` and `.[browser-auth]` installed,
   integration test 10 passes:
   `uv run pytest tests/test_oauth.py::test_real_login_returns_jwt_with_correct_audience -v`
4. The MCP tool `login_oauth` is callable via MCP Inspector and returns a
   well-formed JWT (3 dot-separated base64 segments).
5. Decoded JWT `aud` is exactly `"https://api.twojetenis.pl"`.
6. `refresh_oauth_token` returns a new access token without launching a
   browser.
7. Without `playwright` installed, `login_oauth` returns
   `{"success": False, "code": "OAUTH_PLAYWRIGHT_REQUIRED", ...}`
   instead of crashing.
8. `uvx ruff check src/ tests/` passes.
9. No secrets in commits; only env-var documentation in `.env.example`.
10. Legacy `login` tool and all PHPSESSID-based endpoints still work
    end-to-end against `old.twojtenis.pl` (manual smoke-test via MCP
    Inspector).

---

## Workflow for Claude Code

1. **Read the codebase.** `client.py`, `config.py`,
   `endpoints/reservations.py`, `server.py`. Match the style — async httpx,
   `ApiErrorException` raised from low-level code, `{"success": bool, ...}`
   shapes returned from MCP tools, singleton endpoints, `config.get()`.

2. **Install dev deps.** `uv sync` then
   `uv pip install -e ".[browser-auth]" && uv run playwright install chromium`.

3. **Write tests first** (`tests/test_oauth.py`, all 9 unit tests). They
   should fail because `oauth_client.py` doesn't exist yet.

4. **Implement `OAuthClient`** in `src/twojtenis_mcp/oauth_client.py`,
   stubbing the browser call. Tests 1, 2, 6, 7 should pass with a mocked
   browser.

5. **Implement the browser module** in
   `src/twojtenis_mcp/oauth_browser.py`. Tests 3, 4, 5 should pass.

6. **Add the endpoint and MCP tools** (`endpoints/oauth.py`, additions to
   `server.py`). Tests 8 and 9 should pass.

7. **Update config** (`config.py`) and `.env.example`.

8. **Run integration test 10** if `.env` has credentials.
   - If it fails on the audience assertion, you got the typo wrong;
     re-check the value in `config.auth0_audience`.
   - If the browser times out, run with `AUTH0_BROWSER_HEADLESS=false` and
     watch — likely a selector mismatch. Save a screenshot on timeout for
     debugging (the spec mentions this).

9. **Manual smoke-test via MCP Inspector:**
   ```
   npx @modelcontextprotocol/inspector uv run -m twojtenis_mcp.server
   ```
   Call `login_oauth(email, password)`. Decode the returned `access_token`
   at jwt.io. Verify `aud`, `iss`, `exp`. Call `refresh_oauth_token` with
   the returned `refresh_token`. Verify a new access token returns without
   the browser launching.

10. **Update `README.md`, `CLAUDE.md`, `pyproject.toml`.**

11. **Quality gate:**
    ```
    uv run pytest tests/
    uvx ruff check src/ tests/
    ```

12. **Commit** when green. Suggested message:
    ```
    feat(auth): add Auth0 OIDC login for api.twojetenis.pl

    - OAuthClient drives Auth0 Universal Login via headless Chromium
      (tenant disables ROPC) and exchanges the auth code for a JWT
    - refresh_oauth_token uses pure HTTP, no browser
    - Playwright is an optional dep ([browser-auth] extras)
    - Legacy PHPSESSID flow unchanged
    ```

---

## Out of scope

- Migrating existing endpoints (`get_reservations`, `put_reservation`, etc.)
  to the new JSON API. Separate effort.
- Server-side token caching across MCP tool calls. Stateless design
  preserved — clients hold and pass tokens.
- Refresh-token rotation handling beyond what Auth0 returns.
- Multi-account support.
- Storing tokens in the OS keychain.

---

## Quick reference: production values

```
domain        = twojtenis.eu.auth0.com
client_id     = 86BsGMVf8imqTkuKVkxeW2FalNALsO4y
audience      = https://api.twojetenis.pl     ← typo intentional
redirect_uri  = https://app.twojtenis.pl
scope         = openid profile email offline_access
flow          = authorization_code + PKCE (S256), no client_secret
ROPC          = disabled (verified)
```
