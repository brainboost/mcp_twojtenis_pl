"""Playwright-driven Auth0 Universal Login. Lazy-imported by oauth_client.py
so users don't pay the dependency cost unless login() is actually called."""

import sys
import tempfile
import urllib.parse
from typing import Any

# Required on Linux (Lambda, containers, CI) — Chromium's sandbox and shared
# memory features don't exist in those environments.
_LINUX_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--single-process",
]


class OAuthBrowserError(Exception):
    """Raised when the browser-driven login flow fails."""

    def __init__(self, message: str, kind: str) -> None:
        super().__init__(message)
        self.kind = kind


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
    executable_path: str | None = None,
) -> str:
    """Drive the Auth0 Universal Login form, intercept the redirect, return the auth code.

    Returns:
        The ``code`` query parameter from the redirect URL.

    Raises:
        ImportError: if playwright is not installed.
        OAuthBrowserError(message, kind) where kind is:
            'invalid_credentials' - explicit login rejection appeared
            'timeout'             - redirect didn't fire within timeout_s
            'unexpected'          - anything else
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise ImportError(
            "playwright is not installed. Run: "
            "uv pip install -e '.[browser-auth]' && uv run playwright install chromium"
        ) from exc

    params: dict[str, Any] = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "audience": audience,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    authorize_url = f"https://{domain}/authorize?{urllib.parse.urlencode(params)}"

    captured_code: list[str] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            executable_path=executable_path or None,
            args=_LINUX_LAUNCH_ARGS if sys.platform == "linux" else [],
        )
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Register request interception BEFORE navigating
            def _on_request(request: Any) -> None:
                url = request.url
                if url.startswith(redirect_uri):
                    parsed = urllib.parse.urlparse(url)
                    qs = urllib.parse.parse_qs(parsed.query)
                    code_values = qs.get("code")
                    if code_values:
                        captured_code.append(code_values[0])

            page.on("request", _on_request)

            await page.goto(authorize_url, timeout=timeout_s * 1000)

            # Wait for the username field, then fill it
            email_locator = page.locator(
                'input[name="username"], input[name="email"], input[type="email"]'
            ).first  # .first is a property, not a method
            await email_locator.wait_for(state="visible", timeout=30_000)
            await email_locator.fill(email)

            # Wait for the password field (may appear after an initial email-only step)
            password_locator = page.locator(
                'input[name="password"], input[type="password"]'
            ).first
            await password_locator.wait_for(state="visible", timeout=10_000)
            await password_locator.click()
            # press_sequentially types character-by-character, firing all keyboard
            # events — more reliable than fill() on React-controlled inputs.
            await password_locator.press_sequentially(password, delay=30)

            # Click the submit / Log In button
            submit_locator = page.locator(
                'button[type="submit"], button[name="action"][value="default"]'
            ).first
            await submit_locator.wait_for(state="visible")
            await submit_locator.click()

            # Wait for redirect or error banner
            timeout_ms = timeout_s * 1000
            elapsed_ms = 0
            poll_ms = 300

            # Broad selector — catches Auth0 ULP alert variants across tenant configs
            _ERROR_SELECTOR = (
                '[role="alert"], '
                ".ulp-alert-error, "
                '[data-testid="error"], '
                '[class*="error"], '
                '[class*="alert-danger"], '
                'p[class*="error"], '
                'span[class*="error"]'
            )

            while elapsed_ms < timeout_ms:
                if captured_code:
                    return captured_code[0]

                # Check for error banner (invalid credentials)
                error_el = page.locator(_ERROR_SELECTOR)
                try:
                    await error_el.first.wait_for(state="visible", timeout=poll_ms)
                    raise OAuthBrowserError(
                        "Auth0 rejected credentials: invalid username or password",
                        kind="invalid_credentials",
                    )
                except Exception as exc:
                    if isinstance(exc, OAuthBrowserError):
                        raise
                    # Not visible yet; keep polling

                elapsed_ms += poll_ms

            if not captured_code:
                # Capture screenshot for debugging
                screenshot_path = tempfile.mkstemp(suffix=".png")
                try:
                    await page.screenshot(path=screenshot_path[1])
                except Exception:
                    screenshot_path = "(screenshot failed)"
                raise OAuthBrowserError(
                    f"Timed out waiting for Auth0 redirect after {timeout_s}s. "
                    f"Screenshot: {screenshot_path}",
                    kind="timeout",
                )

            return captured_code[0]

        except OAuthBrowserError:
            raise
        except Exception as exc:
            raise OAuthBrowserError(
                f"Unexpected error during browser login: {exc}",
                kind="unexpected",
            ) from exc
        finally:
            await context.close()
            await browser.close()
