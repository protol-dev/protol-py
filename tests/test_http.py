"""Tests for the internal HTTP client."""

from __future__ import annotations

import pytest
import httpx

from protol._http import HttpClient, AsyncHttpClient, _build_headers, _handle_error_response
from protol.constants import SDK_VERSION
from protol.exceptions import (
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)


class TestBuildHeaders:
    def test_headers_contain_auth(self):
        headers = _build_headers("test_key")
        assert headers["Authorization"] == "Bearer test_key"

    def test_headers_contain_user_agent(self):
        headers = _build_headers("test_key")
        assert headers["User-Agent"] == f"protol-py/{SDK_VERSION}"

    def test_headers_contain_content_type(self):
        headers = _build_headers("test_key")
        assert headers["Content-Type"] == "application/json"


class TestHandleErrorResponse:
    def _make_response(self, status_code, json_body=None, headers=None):
        """Create a mock httpx.Response."""
        return httpx.Response(
            status_code=status_code,
            json=json_body or {"error": {"message": "test error"}},
            headers=headers or {},
        )

    def test_401_raises_auth_error(self):
        response = self._make_response(401)
        with pytest.raises(AuthenticationError):
            _handle_error_response(response)

    def test_404_raises_not_found(self):
        response = self._make_response(404)
        with pytest.raises(NotFoundError):
            _handle_error_response(response)

    def test_422_raises_validation_error(self):
        response = self._make_response(422)
        with pytest.raises(ValidationError):
            _handle_error_response(response)

    def test_429_raises_rate_limit_error(self):
        response = self._make_response(
            429,
            headers={"Retry-After": "30"},
        )
        with pytest.raises(RateLimitError) as exc_info:
            _handle_error_response(response)
        assert exc_info.value.retry_after_seconds == 30.0

    def test_429_without_retry_after(self):
        response = self._make_response(429)
        with pytest.raises(RateLimitError) as exc_info:
            _handle_error_response(response)
        assert exc_info.value.retry_after_seconds is None

    def test_500_raises_server_error(self):
        response = self._make_response(500)
        with pytest.raises(ServerError) as exc_info:
            _handle_error_response(response)
        assert exc_info.value.status_code == 500

    def test_503_raises_server_error(self):
        response = self._make_response(503)
        with pytest.raises(ServerError) as exc_info:
            _handle_error_response(response)
        assert exc_info.value.status_code == 503


class TestHttpClient:
    def test_initialization(self):
        client = HttpClient(
            api_key="test_key",
            base_url="https://test.example.com/v1",
            timeout=10,
            max_retries=2,
        )
        assert client._base_url == "https://test.example.com/v1"
        assert client._max_retries == 2
        client.close()

    def test_get_success(self, httpx_mock):
        httpx_mock.add_response(
            url="https://test.example.com/v1/test",
            json={"result": "ok"},
        )
        client = HttpClient(
            api_key="test_key",
            base_url="https://test.example.com/v1",
            max_retries=0,
        )
        result = client.get("/test")
        assert result == {"result": "ok"}
        client.close()

    def test_post_success(self, httpx_mock):
        httpx_mock.add_response(
            url="https://test.example.com/v1/test",
            json={"id": "123"},
        )
        client = HttpClient(
            api_key="test_key",
            base_url="https://test.example.com/v1",
            max_retries=0,
        )
        result = client.post("/test", json={"name": "test"})
        assert result == {"id": "123"}
        client.close()

    def test_401_raises_auth_error(self, httpx_mock):
        httpx_mock.add_response(
            url="https://test.example.com/v1/test",
            status_code=401,
            json={"error": {"message": "Unauthorized"}},
        )
        client = HttpClient(
            api_key="test_key",
            base_url="https://test.example.com/v1",
            max_retries=0,
        )
        with pytest.raises(AuthenticationError):
            client.get("/test")
        client.close()

    def test_404_raises_not_found(self, httpx_mock):
        httpx_mock.add_response(
            url="https://test.example.com/v1/agents/agt_notfound",
            status_code=404,
            json={"error": {"message": "Not found"}},
        )
        client = HttpClient(
            api_key="test_key",
            base_url="https://test.example.com/v1",
            max_retries=0,
        )
        with pytest.raises(NotFoundError):
            client.get("/agents/agt_notfound")
        client.close()

    def test_retry_on_500(self, httpx_mock):
        # First call returns 500, second returns success
        httpx_mock.add_response(
            url="https://test.example.com/v1/test",
            status_code=500,
            json={"error": {"message": "Server error"}},
        )
        httpx_mock.add_response(
            url="https://test.example.com/v1/test",
            json={"result": "ok"},
        )
        client = HttpClient(
            api_key="test_key",
            base_url="https://test.example.com/v1",
            max_retries=1,
        )
        result = client.get("/test")
        assert result == {"result": "ok"}
        client.close()

    def test_close(self):
        client = HttpClient(api_key="test_key", base_url="https://test.example.com/v1")
        client.close()  # Should not raise


class TestAsyncHttpClient:
    @pytest.mark.asyncio
    async def test_initialization(self):
        client = AsyncHttpClient(
            api_key="test_key",
            base_url="https://test.example.com/v1",
        )
        assert client._base_url == "https://test.example.com/v1"
        await client.close()

    @pytest.mark.asyncio
    async def test_get_success(self, httpx_mock):
        httpx_mock.add_response(
            url="https://test.example.com/v1/test",
            json={"result": "ok"},
        )
        client = AsyncHttpClient(
            api_key="test_key",
            base_url="https://test.example.com/v1",
            max_retries=0,
        )
        result = await client.get("/test")
        assert result == {"result": "ok"}
        await client.close()

    @pytest.mark.asyncio
    async def test_close(self):
        client = AsyncHttpClient(
            api_key="test_key",
            base_url="https://test.example.com/v1",
        )
        await client.close()
