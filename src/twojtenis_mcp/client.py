"""HTTP client for TwojTenis.pl API."""

# import asyncio
import json
import logging
import re
from collections.abc import Callable
from typing import Any

import httpx

from .config import config
from .models import ApiErrorException

logger = logging.getLogger(__name__)


async def with_session_retry(
    operation: Callable, session_manager, *args, **kwargs
) -> Any:
    """Execute an operation with session retry logic on server errors.

    Args:
        operation: The async function to execute
        session_manager: SessionManager instance for refreshing sessions
        *args: Arguments to pass to the operation
        **kwargs: Keyword arguments to pass to the operation

    Returns:
        Result of the operation

    Raises:
        ApiErrorException: If operation fails after retry attempts
    """
    max_retries = 1  # One retry after session refresh
    last_exception = ApiErrorException(
        code="UNKNOWN_ERROR",
        message="Unknown error occurred",
    )

    for attempt in range(max_retries + 1):
        try:
            # Get current session
            session = await session_manager.get_session()
            if not session:
                raise ApiErrorException(
                    code="NO_SESSION",
                    message="No active session available",
                )

            # Execute the operation with current session
            result = await operation(*args, phpsessid=session.phpsessid, **kwargs)
            return result

        except ApiErrorException as e:
            last_exception = e

            # If this is a server/auth error and we haven't retried yet, try refreshing session
            if attempt < max_retries and (
                e.code in ["HTTP_ERROR", "AUTH_ERROR", "REQUEST_FAILED"]
                or (
                    e.code == "HTTP_ERROR"
                    and any(
                        code in str(e) for code in ["401", "403", "500", "502", "503"]
                    )
                )
            ):
                logger.warning(
                    f"Server error on attempt {attempt + 1}, refreshing session: {e.message}"
                )
                await session_manager.refresh_session()
                continue
            else:
                # No more retries or non-retryable error
                break

        except Exception as e:
            last_exception = ApiErrorException(
                code="UNEXPECTED_ERROR",
                message=f"Unexpected error: {str(e)}",
            )
            break

    # All attempts failed
    raise last_exception


class TwojTenisClient:
    """HTTP client for interacting with TwojTenis.pl API."""

    def __init__(self):
        """Initialize HTTP client."""
        self.base_url = config.base_url
        self.timeout = config.request_timeout
        self.retry_delay = config.retry_delay
        self.static_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
            "Accept": "*/*",
            "Accept-Language": "en,pl;q=0.7,ru;q=0.3",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
        phpsessid: str | None = None,
    ) -> tuple[Any | None, dict[str, str] | None]:
        """Make HTTP request

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            params: URL parameters
            data: Request data
            form_data: Form data for multipart requests
            phpsessid: PHP session ID for authentication

        Returns:
            Tuple of (response_data, response_headers)
        """
        # Prepare headers
        request_headers = dict(self.static_headers)
        if headers:
            request_headers.update(headers)

        # Add session cookie if provided
        if phpsessid:
            request_headers["Cookie"] = f"PHPSESSID={phpsessid}; CooAcc=1"

        # Prepare request data
        request_data = None
        if form_data:
            # For multipart form data
            request_data = form_data
        elif data:
            # For URL-encoded form data
            request_data = data
            if "Content-Type" not in request_headers:
                request_headers["Content-Type"] = "application/x-www-form-urlencoded"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    params=params,
                    data=request_data,
                )

                # Extract response headers
                response_headers = dict(response.headers)

                # Handle response based on content type
                content_type = response.headers.get("content-type", "").lower()

                if "application/json" in content_type:
                    response_data = response.json()
                elif "text/html" in content_type:
                    response_data = response.text
                else:
                    response_data = response.content

                # Check for successful response
                if response.status_code >= 200 and response.status_code < 300:
                    return response_data, response_headers

                logger.warning(f"HTTP {response.status_code}: {response.text[:200]}")

                raise ApiErrorException(
                    code="HTTP_ERROR",
                    message=f"HTTP {response.status_code}",
                    details={"response": response.text[:500]},
                )

        except httpx.RequestError as e:
            logger.warning(f"Request failed: {e}")
            raise ApiErrorException(
                code="REQUEST_FAILED",
                message=f"{method} request failed for {url}",
                details={"error": str(e)},
            ) from e

    # async def _make_retriable_request(
    #     self,
    #     method: str,
    #     url: str,
    #     headers: dict[str, str] | None = None,
    #     params: dict[str, Any] | None = None,
    #     data: dict[str, Any] | None = None,
    #     form_data: dict[str, Any] | None = None,
    #     phpsessid: str | None = None,
    # ) -> tuple[Any | None, dict[str, str] | None]:
    #     """Make HTTP request with retry logic.

    #     Args:
    #         method: HTTP method
    #         url: Request URL
    #         headers: Request headers
    #         params: URL parameters
    #         data: Request data
    #         form_data: Form data for multipart requests
    #         phpsessid: PHP session ID for authentication

    #     Returns:
    #         Tuple of (response_data, response_headers)
    #     """
    #     # Make request with retry logic
    #     last_exception = None
    #     retry_attempts = config.retry_attempts
    #     for attempt in range(retry_attempts):
    #         try:
    #             response_data, _ = await self._make_request(
    #                 method=method,
    #                 url=url,
    #                 headers=headers,
    #                 params=params,
    #                 data=data,
    #                 form_data=form_data,
    #                 phpsessid=phpsessid,
    #             )

    #         except Exception as e:
    #             last_exception = e
    #             logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
    #             if attempt < retry_attempts - 1:
    #                 await asyncio.sleep(self.retry_delay * (2**attempt))
    #                 continue
    #             break

    #     # All attempts failed
    #     if last_exception:
    #         raise ApiErrorException(
    #             code="REQUEST_FAILED",
    #             message=f"Request failed after {retry_attempts} attempts",
    #             details={"error": str(last_exception)},
    #         )
    #     else:
    #         raise ApiErrorException(
    #             code="REQUEST_FAILED",
    #             message=f"Request failed after {retry_attempts} attempts",
    #             details={},
    #         )

    async def login(self, email: str, password: str) -> str | None:
        """Login to TwojTenis.pl and return PHPSESSID.

        Args:
            email: User email
            password: User password

        Returns:
            PHPSESSID if login successful, None otherwise
        """
        url = f"{self.base_url}/pl/login.html"

        data = {
            "login": email,
            "pass": password,
            "back_url": "/pl/home.html",
            "action": "login",
        }

        headers = {
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/pl/",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Priority": "u=0, i",
        }
        request_headers = dict(self.static_headers)
        request_headers.update(headers)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method="POST",
                    url=url,
                    headers=request_headers,
                    data=data,
                )
                # Check for successful response
                # redirect after successful authentication
                if response.status_code == 302:
                    # Extract response headers
                    response_headers = dict(response.headers)

                    # Extract PHPSESSID from Set-Cookie header
                    set_cookie = response_headers.get("set-cookie", "")  # type: ignore
                    phpsessid_match = re.search(r"PHPSESSID=([^;]+)", set_cookie)

                    if phpsessid_match:
                        phpsessid = phpsessid_match.group(1)
                        logger.info(f"Login successful, PHPSESSID: {phpsessid[:8]}...")
                        return phpsessid

                logger.error("No PHPSESSID found in response")
                return None

        except ApiErrorException as e:
            logger.error(f"Login failed: {e.message}")
            return None

    async def keep_logged(self, phpsessid: str) -> bool:
        """Keep session alive.

        Args:
            phpsessid: PHP session ID

        Returns:
            True if session is still valid, False otherwise
        """
        url = f"{self.base_url}/ajax.php?load=keep_logged"

        headers = {
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/pl/home.html",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "TE": "trailers",
        }
        request_headers = dict(self.static_headers)
        request_headers.update(headers)

        try:
            _response_data, _ = await self._make_request(
                method="POST",
                url=url,
                headers=request_headers,
                phpsessid=phpsessid,
            )

            # If we get here without authentication error, session is valid
            logger.debug("Session keep-alive successful")
            return True

        except ApiErrorException as e:
            if e.code == "AUTH_ERROR":
                logger.warning("Session expired")
                return False
            else:
                logger.error(f"Keep logged failed: {e.message}")
                return False

    async def get_club_schedule(
        self,
        club_url: str,
        sport_id: int,
        date: str,
        phpsessid: str,
    ) -> str | None:
        """Get club schedule for specific date and sport.

        Args:
            club_url: Club URL identifier
            sport_id: Sport ID (84=badminton, 70=tennis)
            date: Date in DD.MM.YYYY format
            phpsessid: PHP session ID

        Returns:
            Schedule data if successful, None otherwise
        """
        url = f"{self.base_url}/ajax.php?load=courts_list"

        data = {
            "date": date,
            "club_url": club_url,
            "page": "NaN",
            "spr": sport_id,
            "zsh": "0",
            "tz": "0",
        }

        headers = {
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/pl/kluby/{club_url}.html",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "TE": "trailers",
        }

        try:
            response_data, _ = await self._make_request(
                method="POST",
                url=url,
                data=data,
                headers=headers,
                phpsessid=phpsessid,
            )
            logger.debug(f"Schedule retrieved for {club_url} on {date}")
            return response_data

        except ApiErrorException as e:
            logger.error(f"Failed to get club schedule: {e.message}")
            return None

    async def get_reservations(self, phpsessid: str) -> str | None:
        """Get user's current reservations.

        Args:
            phpsessid: PHP session ID

        Returns:
            HTML response with reservations if successful, None otherwise
        """
        url = f"{self.base_url}/pl/dashboard/reservations.html"

        headers = {
            "Referer": f"{self.base_url}/pl/dashboard/account.html",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Priority": "u=0, i",
            "TE": "trailers",
        }

        try:
            response_data, _ = await self._make_request(
                method="GET",
                url=url,
                headers=headers,
                phpsessid=phpsessid,
            )

            logger.debug("Reservations retrieved successfully")
            return response_data

        except ApiErrorException as e:
            logger.error(f"Failed to get reservations: {e.message}")
            return None

    async def make_reservation(
        self,
        club_id: str,
        sport_id: int,
        court_number: int,
        date: str,
        hour: str,
        phpsessid: str,
    ) -> bool:
        """Make a court reservation.

        Args:
            club_id: Club ID
            sport_id: Sport ID
            court_number: Court number
            date: Date in DD.MM.YYYY format
            hour: Hour in HH:MM format
            phpsessid: PHP session ID

        Returns:
            True if reservation successful, False otherwise
        """
        url = f"{self.base_url}/pl/rsv/make.html"

        # Prepare reservation data
        date_key = date.replace(".", "")
        reservation_key = (
            f"rsv_{date_key}_{sport_id}_{court_number}_{hour.replace(':', '_')}"
        )
        reservation_value = {
            "sport_id": sport_id,
            "cort_id": court_number,
            "date": date,
            "hour": hour,
        }

        form_data = {
            "club_id": club_id,
            "type": "corts",
            reservation_key: json.dumps(reservation_value),
        }

        headers = {
            "Referer": f"{self.base_url}/pl/kluby/{club_id}.html",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Priority": "u=0, i",
            "TE": "trailers",
        }

        try:
            response_data, _ = await self._make_request(
                method="POST",
                url=url,
                form_data=form_data,
                headers=headers,
                phpsessid=phpsessid,
            )

            # Check if reservation was successful (this would need to be based on actual response)
            logger.info(
                f"Reservation made for club {club_id}, court {court_number} on {date} at {hour}"
            )
            return True

        except ApiErrorException as e:
            logger.error(f"Failed to make reservation: {e.message}")
            return False

    async def delete_reservation(
        self,
        club_id: str,
        sport_id: int,
        court_number: int,
        date: str,
        hour: str,
        phpsessid: str,
    ) -> bool:
        """Delete a court reservation.

        Args:
            club_id: Club ID
            sport_id: Sport ID
            court_number: Court number
            date: Date in DD.MM.YYYY format
            hour: Hour in HH:MM format
            phpsessid: PHP session ID

        Returns:
            True if deletion successful, False otherwise
        """
        # This is an assumption based on the requirements
        # The actual endpoint might be different
        url = f"{self.base_url}/pl/rsv/delete.html"

        # Prepare deletion data (assuming similar format to make reservation)
        date_key = date.replace(".", "")
        reservation_key = (
            f"rsv_{date_key}_{sport_id}_{court_number}_{hour.replace(':', '_')}"
        )
        reservation_value = {
            "sport_id": sport_id,
            "cort_id": court_number,
            "date": date,
            "hour": hour,
        }

        data = {
            "club_id": club_id,
            "type": "corts",
            reservation_key: json.dumps(reservation_value),
            "action": "delete",
        }

        headers = {
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/pl/dashboard/reservations.html",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "TE": "trailers",
        }

        try:
            response_data, _ = await self._make_request(
                method="POST",
                url=url,
                data=data,
                headers=headers,
                phpsessid=phpsessid,
            )

            # Check if deletion was successful (this would need to be based on actual response)
            logger.info(
                f"Reservation deleted for club {club_id}, court {court_number} on {date} at {hour}"
            )
            return True

        except ApiErrorException as e:
            logger.error(f"Failed to delete reservation: {e.message}")
            return False
