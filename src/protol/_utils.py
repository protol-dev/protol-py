"""Internal utility functions for the Protol SDK."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def hash_data(data: Any) -> str:
    """Create a SHA-256 hash of any data.

    Handles: str, bytes, dict, list, Pydantic models, and other serializable types.
    Converts to a canonical JSON string first, then hashes.

    Args:
        data: The data to hash.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    if data is None:
        return hashlib.sha256(b"null").hexdigest()

    if isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()

    if isinstance(data, str):
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    # Handle Pydantic models
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    elif hasattr(data, "dict"):
        data = data.dict()

    # Convert to canonical JSON (sorted keys, no whitespace)
    try:
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        canonical = str(data)

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_agent_id(agent_id: str) -> bool:
    """Validate agent ID format: 'agt_' followed by 6-12 alphanumeric chars.

    Args:
        agent_id: The agent ID to validate.

    Returns:
        True if valid, False otherwise.
    """
    return bool(re.match(r"^agt_[a-zA-Z0-9]{6,12}$", agent_id))


def validate_api_key(api_key: str) -> bool:
    """Validate API key format: 'aos_sk_' followed by 20+ chars.

    Args:
        api_key: The API key to validate.

    Returns:
        True if valid, False otherwise.
    """
    return bool(re.match(r"^aos_sk_.{20,}$", api_key))


def calculate_size_bytes(data: Any) -> int:
    """Calculate byte size of data when serialized as JSON.

    Args:
        data: The data to measure.

    Returns:
        Size in bytes.
    """
    if data is None:
        return 0

    if isinstance(data, bytes):
        return len(data)

    if isinstance(data, str):
        return len(data.encode("utf-8"))

    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    elif hasattr(data, "dict"):
        data = data.dict()

    try:
        return len(json.dumps(data, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        return len(str(data).encode("utf-8"))


def truncate(s: str, max_length: int) -> str:
    """Truncate string to max_length with ellipsis.

    Args:
        s: The string to truncate.
        max_length: Maximum length (must be >= 4 for ellipsis to fit).

    Returns:
        Truncated string with '...' suffix if it was longer than max_length.
    """
    if len(s) <= max_length:
        return s
    if max_length < 4:
        return s[:max_length]
    return s[: max_length - 3] + "..."
