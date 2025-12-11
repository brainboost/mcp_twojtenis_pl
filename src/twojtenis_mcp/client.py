import re
from collections.abc import Callable
from typing import Any

import httpx

from .config import config
from .models import ApiErrorException
from .utils import extract_id_from_url


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

    async def with_session_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute an operation with retry logic on server errors.

        Args:
            operation: The async function to execute
            *args: Arguments to pass to the operation
            **kwargs: Keyword arguments to pass to the operation

        Returns:
            Result of the operation

        Raises:
            ApiErrorException: If operation fails after retry attempts
        """
        max_retries = config.retry_attempts | 1
        last_exception = ApiErrorException(
            code="UNKNOWN_ERROR",
            message="Unknown error occurred",
        )

        for attempt in range(max_retries + 1):
            try:
                session = kwargs["session_id"]
                if not session:
                    raise ApiErrorException(
                        code="AUTHENTICATION_REQUIRED",
                        message="Authentication required. Use login and pass session_id to authenticate.",
                    )
                result = await operation(*args, **kwargs)
                return result

            except ApiErrorException as e:
                last_exception = e

                # If this is a server error and we haven't retried yet
                if attempt < max_retries and (
                    e.code
                    in [
                        "HTTP_ERROR",
                        "REQUEST_FAILED",
                    ]
                    or (
                        e.code == "HTTP_ERROR"
                        and any(code in str(e) for code in ["500", "502", "503"])
                    )
                ):
                    attempt += 1
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
        raise last_exception

    async def _make_request(
        self,
        sessid: str,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
    ) -> tuple[Any | None, dict[str, str] | None]:
        """Make HTTP request

        Args:
            sessid: user's session ID for authentication
            method: HTTP method
            url: Request URL
            headers: Request headers
            params: URL parameters
            data: Request data
            form_data: Form data for multipart requests

        Returns:
            Tuple of (response_data, response_headers)
        """
        request_headers = dict(self.static_headers)
        if headers:
            request_headers.update(headers)

        if not sessid:
            raise ApiErrorException(
                code="NO_SESSION",
                message="No active user session available",
            )
        request_headers["Cookie"] = f"PHPSESSID={sessid}; CooAcc=1"

        request_data = None
        if form_data:
            request_data = form_data
        elif data:
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

                response_headers = dict(response.headers)
                content_type = response.headers.get("content-type", "").lower()

                if "application/json" in content_type:
                    response_data = response.json()
                elif "text/html" in content_type:
                    response_data = response.text
                else:
                    response_data = response.content

                if response.status_code >= 200 and response.status_code < 303:
                    return response_data, response_headers

                raise ApiErrorException(
                    code="HTTP_ERROR",
                    message=f"HTTP {response.status_code}",
                    details={"response": response.text[:500]},
                )

        except httpx.RequestError as e:
            raise ApiErrorException(
                code="REQUEST_FAILED",
                message=f"{method} request failed for {url}",
                details={"error": str(e)},
            ) from e

    async def login(self, email: str, password: str) -> str | None:
        """Login to TwojTenis.pl and return session ID.

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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method="POST",
                url=url,
                headers=request_headers,
                data=data,
            )
            # redirect after successful authentication
            if response.status_code == 302:
                response_headers = dict(response.headers)
                # Extract PHPSESSID from Set-Cookie header
                set_cookie = response_headers.get("set-cookie", "")  # type: ignore
                phpsessid_match = re.search(r"PHPSESSID=([^;]+)", set_cookie)

                if phpsessid_match:
                    phpsessid = phpsessid_match.group(1)
                    return phpsessid

            # No PHPSESSID found in response
            return None

    async def get_club_info(
        self,
        session_id: str,
        club_id: str,
    ) -> str | None:
        """Get club's information, working hours table.

        Args:
            session_id: Logged user's session ID
            club_id: Club identifier

        Returns:
            Club information
        """

        url = f"{self.base_url}/pl/kluby/{club_id}/courts_list.html"
        headers = {
            "Referer": f"{self.base_url}/pl/home.html",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Priority": "u=0, i",
        }
        response_data, _ = await self._make_request(
            sessid=session_id,
            method="GET",
            url=url,
            headers=headers,
        )
        return response_data

    async def get_club_schedule(
        self,
        session_id: str,
        club_id: str,
        sport_id: int,
        date: str,
    ) -> str | None:
        """Get club schedule for specific date and sport.

        Args:
            session_id: Logged user's session ID
            club_id: Club identifier
            sport_id: Sport ID
            date: Date in DD.MM.YYYY format

        Returns:
            Schedule data if successful, None otherwise
        """
        url = f"{self.base_url}/ajax.php?load=courts_list"

        data = {
            "date": date,
            "club_url": club_id,
            "page": "NaN",
            "spr": sport_id,
            "zsh": "0",
            "tz": "0",
        }

        headers = {
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/pl/kluby/{club_id}.html",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "TE": "trailers",
        }

        response_data, _ = await self._make_request(
            sessid=session_id,
            method="POST",
            url=url,
            data=data,
            headers=headers,
        )
        return response_data

    async def get_reservations(self, session_id: str) -> str | None:
        """Get user's current reservations.

        Args:
            session_id: Logged user's session ID

        Returns:
            HTML response with reservations if successful, None otherwise
        """
        url = f"{self.base_url}/pl/dashboard/reservations.html"

        headers = {
            "Referer": f"{self.base_url}/pl/dashboard/reservations.html",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Priority": "u=0, i",
            "TE": "trailers",
        }
        response_data, _ = await self._make_request(
            sessid=session_id,
            method="GET",
            url=url,
            headers=headers,
        )
        return response_data

    async def get_reservation(self, session_id: str, booking_id: str) -> str | None:
        """
        Get user's reservation by ID

        Args:
            session_id: Logged user's session ID
            booking_id: Reservation ID

        Returns:
            HTML response with reservations if successful, None otherwise
        """
        url = f"{self.base_url}/pl/rsv/show/{booking_id}.html"

        headers = {
            "Referer": f"{self.base_url}/pl/dashboard/reservations/past.html",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Priority": "u=0, i",
            "TE": "trailers",
        }

        response_data, _headers = await self._make_request(
            sessid=session_id,
            method="GET",
            url=url,
            headers=headers,
        )
        return response_data

    async def make_reservation(
        self,
        session_id: str,
        club_num: int,
        sport_id: int,
        court_number: int,
        date: str,
        start_time: str,
        end_time: str,
    ) -> str | None:
        """Make a court reservation.

        Args:
            session_id: Logged user's session ID
            club_num: Club number
            sport_id: Sport ID
            court_number: Court number starting from 1
            date: Date in DD.MM.YYYY format
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format

        Returns:
            Reservation ID if reservation successful, None otherwise
        """
        url = f"{self.base_url}/pl/rsv/make.html"
        form_data = {
            "rsv_usernote_1": "",
            "rsv_date_1": date,
            "rsv_sport_1": sport_id,
            "rsv_cort_1": court_number,
            "rsv_hourfrom_1": start_time,
            "rsv_hourto_1": end_time,
            "rsv_price_1": "100",
            "rsv_dis_1": "0",
            "rsv_disu_1": "",
            "rsv_dist_1": "",
            "back_to": "e",
            "action": "add_rsv",
            "club_id": club_num,
        }

        headers = {
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Priority": "u=0, i",
            "TE": "trailers",
        }

        _, _headers = await self._make_request(
            sessid=session_id,
            method="POST",
            url=url,
            form_data=form_data,
            headers=headers,
        )
        if _headers is not None:
            booking_id = extract_id_from_url(_headers.get("location", ""))
            return booking_id
        return None

    async def delete_reservation(
        self,
        session_id: str,
        booking_id: str,
    ) -> bool:
        """Delete a court reservation.

        Args:
            book_id: Reservation ID

        Returns:
            True if deletion successful, False otherwise
        """
        if not booking_id:
            return False

        url = f"{self.base_url}/pl/rsv/del/{booking_id}.html?back=/pl/dashboard/reservations.html"

        headers = {
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/pl/rsv/show/{booking_id}.html",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "TE": "trailers",
        }

        try:
            _response_data, _ = await self._make_request(
                sessid=session_id,
                method="GET",
                url=url,
                headers=headers,
            )
            return True

        except ApiErrorException:
            return False
