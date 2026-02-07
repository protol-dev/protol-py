"""Internal HTTP client wrapper for the Protol SDK.

NOT part of the public API. Wraps httpx for sync and async HTTP with automatic
header injection, retries, and error mapping.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx

from protol.constants import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, SDK_VERSION
from protol.exceptions import (
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

logger = logging.getLogger("protol")


def _build_headers(api_key: str) -> dict[str, str]:
    """Build default request headers."""
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": f"protol-py/{SDK_VERSION}",
        "Content-Type": "application/json",
    }


def _handle_error_response(response: httpx.Response) -> None:
    """Map HTTP error status codes to custom exceptions."""
    status = response.status_code

    try:
        body = response.json()
        message = body.get("error", {}).get("message", response.text)
    except Exception:
        message = response.text

    if status == 401:
        raise AuthenticationError(message=message)
    elif status == 404:
        raise NotFoundError(message=message)
    elif status == 422:
        raise ValidationError(message=message)
    elif status == 429:
        retry_after = response.headers.get("Retry-After")
        retry_seconds = float(retry_after) if retry_after else None
        raise RateLimitError(message=message, retry_after_seconds=retry_seconds)
    elif status >= 500:
        raise ServerError(message=message, status_code=status)


class HttpClient:
    """Synchronous HTTP client for the Protol API.

    Internal use only. Handles authentication, retries, and error mapping.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute an HTTP request with retries and error handling."""
        last_exception: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                logger.debug(
                    "HTTP %s %s (attempt %d/%d)",
                    method,
                    path,
                    attempt + 1,
                    self._max_retries + 1,
                )

                response = self._client.request(
                    method=method,
                    url=path,
                    json=json,
                    params=params,
                )

                if response.status_code < 400:
                    try:
                        return response.json()
                    except Exception:
                        return None

                # Retry on 429 and 5xx
                if response.status_code in (429,) or response.status_code >= 500:
                    if attempt < self._max_retries:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            wait = float(retry_after)
                        else:
                            wait = min(2 ** attempt, 30)
                        logger.warning(
                            "Retryable error %d on %s %s. Retrying in %.1fs...",
                            response.status_code,
                            method,
                            path,
                            wait,
                        )
                        time.sleep(wait)
                        continue

                _handle_error_response(response)

            except (
                AuthenticationError,
                NotFoundError,
                ValidationError,
                RateLimitError,
                ServerError,
            ):
                raise
            except httpx.ConnectError as exc:
                last_exception = exc
                if attempt < self._max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        "Connection error on %s %s. Retrying in %.1fs...",
                        method,
                        path,
                        wait,
                    )
                    time.sleep(wait)
                    continue
                raise NetworkError(
                    message=f"Failed to connect after {self._max_retries + 1} attempts: {exc}"
                ) from exc
            except httpx.TimeoutException as exc:
                last_exception = exc
                if attempt < self._max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        "Timeout on %s %s. Retrying in %.1fs...",
                        method,
                        path,
                        wait,
                    )
                    time.sleep(wait)
                    continue
                raise NetworkError(
                    message=f"Request timed out after {self._max_retries + 1} attempts: {exc}"
                ) from exc
            except httpx.HTTPError as exc:
                last_exception = exc
                raise NetworkError(message=f"HTTP error: {exc}") from exc

        # Should not reach here, but just in case
        raise NetworkError(
            message=f"Request failed after {self._max_retries + 1} attempts: {last_exception}"
        )

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a GET request."""
        return self._request("GET", path, params=params)

    def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a POST request."""
        return self._request("POST", path, json=json)

    def patch(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a PATCH request."""
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        """Execute a DELETE request."""
        return self._request("DELETE", path)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()


class AsyncHttpClient:
    """Asynchronous HTTP client for the Protol API.

    Internal use only. Async counterpart of HttpClient.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute an async HTTP request with retries and error handling."""
        import asyncio

        last_exception: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                logger.debug(
                    "HTTP %s %s (attempt %d/%d)",
                    method,
                    path,
                    attempt + 1,
                    self._max_retries + 1,
                )

                response = await self._client.request(
                    method=method,
                    url=path,
                    json=json,
                    params=params,
                )

                if response.status_code < 400:
                    try:
                        return response.json()
                    except Exception:
                        return None

                if response.status_code in (429,) or response.status_code >= 500:
                    if attempt < self._max_retries:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            wait = float(retry_after)
                        else:
                            wait = min(2 ** attempt, 30)
                        logger.warning(
                            "Retryable error %d on %s %s. Retrying in %.1fs...",
                            response.status_code,
                            method,
                            path,
                            wait,
                        )
                        await asyncio.sleep(wait)
                        continue

                _handle_error_response(response)

            except (
                AuthenticationError,
                NotFoundError,
                ValidationError,
                RateLimitError,
                ServerError,
            ):
                raise
            except httpx.ConnectError as exc:
                last_exception = exc
                if attempt < self._max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        "Connection error on %s %s. Retrying in %.1fs...",
                        method,
                        path,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                raise NetworkError(
                    message=f"Failed to connect after {self._max_retries + 1} attempts: {exc}"
                ) from exc
            except httpx.TimeoutException as exc:
                last_exception = exc
                if attempt < self._max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        "Timeout on %s %s. Retrying in %.1fs...",
                        method,
                        path,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                raise NetworkError(
                    message=f"Request timed out after {self._max_retries + 1} attempts: {exc}"
                ) from exc
            except httpx.HTTPError as exc:
                last_exception = exc
                raise NetworkError(message=f"HTTP error: {exc}") from exc

        raise NetworkError(
            message=f"Request failed after {self._max_retries + 1} attempts: {last_exception}"
        )

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute an async GET request."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Execute an async POST request."""
        return await self._request("POST", path, json=json)

    async def patch(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Execute an async PATCH request."""
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> Any:
        """Execute an async DELETE request."""
        return await self._request("DELETE", path)

    async def close(self) -> None:
        """Close the underlying async HTTP client."""
        await self._client.aclose()
