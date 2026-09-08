"""Utility functions for quickbooks_sync."""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from django.utils import timezone as django_timezone


def generate_idempotency_key(
    entity_type: str,
    entity_id: str,
    action: str,
    timestamp: Optional[datetime] = None,
) -> str:
    """
    Generate an idempotency key for a sync operation.

    The key is deterministic based on the entity and action, ensuring
    that the same operation always produces the same key.

    Args:
        entity_type: The type of entity (e.g., 'Customer', 'Invoice')
        entity_id: The ID of the entity
        action: The action being performed (e.g., 'create', 'update')
        timestamp: Optional timestamp to include (for uniqueness).
                   If not provided, the key is deterministic based on
                   entity_type, entity_id, and action only.

    Returns:
        A unique idempotency key string
    """
    if timestamp is not None:
        key_data = f"{entity_type}:{entity_id}:{action}:{timestamp.isoformat()}"
    else:
        key_data = f"{entity_type}:{entity_id}:{action}"
    return hashlib.sha256(key_data.encode()).hexdigest()


def generate_request_id() -> str:
    """Generate a unique request ID for tracking."""
    return str(uuid.uuid4())


def parse_qbo_datetime(datetime_str: str) -> datetime:
    """
    Parse a QuickBooks Online datetime string.

    QBO uses ISO 8601 format with timezone offset.

    Args:
        datetime_str: DateTime string from QBO API

    Returns:
        Parsed datetime object with timezone info
    """
    # Remove 'Z' and replace with '+00:00' for Python compatibility
    if datetime_str.endswith("Z"):
        datetime_str = datetime_str[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(datetime_str)
    except ValueError:
        # Try common QBO formats
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse datetime: {datetime_str}")


def format_qbo_datetime(dt: datetime) -> str:
    """
    Format a datetime for QuickBooks Online API.

    Args:
        dt: Python datetime object

    Returns:
        ISO 8601 formatted string
    """
    if dt.tzinfo is None:
        dt = django_timezone.make_aware(dt)

    return dt.isoformat()


def calculate_token_expiry(expires_in: int = 3600) -> datetime:
    """
    Calculate token expiry time.

    Args:
        expires_in: Seconds until expiry (default: 3600 = 1 hour)

    Returns:
        Datetime when token expires
    """
    return django_timezone.now() + timedelta(seconds=expires_in)


def is_token_expired(expires_at: datetime, buffer_seconds: int = 300) -> bool:
    """
    Check if a token is expired or about to expire.

    Args:
        expires_at: When the token expires
        buffer_seconds: Buffer time before actual expiry (default: 5 minutes)

    Returns:
        True if token is expired or about to expire
    """
    if expires_at is None:
        return True

    now = django_timezone.now()
    return now >= (expires_at - timedelta(seconds=buffer_seconds))


def verify_webhook_signature(
    payload: str,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """
    Verify webhook signature using HMAC.

    Args:
        payload: Raw request body
        signature: Signature to verify
        secret: Webhook secret/verifier token
        algorithm: Hash algorithm (default: sha256)

    Returns:
        True if signature is valid
    """
    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        getattr(hashlib, algorithm),
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging.

    Args:
        data: Sensitive string to mask
        visible_chars: Number of characters to show

    Returns:
        Masked string (e.g., "****1234")
    """
    if not data:
        return data
    if len(data) <= visible_chars:
        return data
    return "*" * (len(data) - visible_chars) + data[-visible_chars:]


def chunk_list(lst: list, chunk_size: int) -> list[list]:
    """
    Split a list into chunks.

    Args:
        lst: List to split
        chunk_size: Maximum size of each chunk

    Returns:
        List of chunks
    """
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Safely serialize data to JSON.

    Handles datetime objects and other non-serializable types.

    Args:
        data: Data to serialize
        **kwargs: Additional arguments for json.dumps

    Returns:
        JSON string
    """

    def default_handler(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(data, default=default_handler, **kwargs)


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix
