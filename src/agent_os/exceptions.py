"""Custom exceptions for the AgentOS SDK."""

from __future__ import annotations


class AgentOSError(Exception):
    """Base exception for all AgentOS errors."""

    def __init__(self, message: str = "", status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(AgentOSError):
    """Raised when API key is invalid or missing."""

    def __init__(self, message: str = "Invalid or missing API key.") -> None:
        super().__init__(message=message, status_code=401)


class NotFoundError(AgentOSError):
    """Raised when requested resource doesn't exist."""

    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(message=message, status_code=404)


class ValidationError(AgentOSError):
    """Raised when input data is invalid."""

    def __init__(self, message: str = "Validation error.") -> None:
        super().__init__(message=message, status_code=422)


class RateLimitError(AgentOSError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded.",
        retry_after_seconds: float | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message=message, status_code=429)


class ServerError(AgentOSError):
    """Raised when the AgentOS API returns a 5xx error."""

    def __init__(self, message: str = "Server error.", status_code: int = 500) -> None:
        super().__init__(message=message, status_code=status_code)


class NetworkError(AgentOSError):
    """Raised when there's a network connectivity issue."""

    def __init__(self, message: str = "Network error.") -> None:
        super().__init__(message=message, status_code=None)


class ActionError(AgentOSError):
    """Raised when there's an error recording an action."""

    def __init__(self, message: str = "Action recording error.") -> None:
        super().__init__(message=message, status_code=None)
