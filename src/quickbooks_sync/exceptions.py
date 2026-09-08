"""Custom exceptions for quickbooks_sync."""

from typing import Any, Optional


class QuickBooksSyncError(Exception):
    """Base exception for quickbooks_sync."""

    def __init__(
        self,
        message: str = "An error occurred in QuickBooks Sync",
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class OAuthError(QuickBooksSyncError):
    """OAuth authentication error."""

    def __init__(
        self,
        message: str = "OAuth authentication failed",
        code: Optional[str] = "OAUTH_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class TokenExpiredError(OAuthError):
    """Access token has expired."""

    def __init__(
        self,
        message: str = "Access token has expired",
        code: Optional[str] = "TOKEN_EXPIRED",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class RefreshTokenExpiredError(OAuthError):
    """Refresh token has expired."""

    def __init__(
        self,
        message: str = "Refresh token has expired. Please reauthorize.",
        code: Optional[str] = "REFRESH_TOKEN_EXPIRED",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class RateLimitError(QuickBooksSyncError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: Optional[str] = "RATE_LIMIT_EXCEEDED",
        details: Optional[dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, code, details)


class SyncError(QuickBooksSyncError):
    """Sync operation error."""

    def __init__(
        self,
        message: str = "Sync operation failed",
        code: Optional[str] = "SYNC_ERROR",
        details: Optional[dict[str, Any]] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(message, code, details)


class ConflictError(SyncError):
    """Sync conflict detected."""

    def __init__(
        self,
        message: str = "Sync conflict detected",
        code: Optional[str] = "CONFLICT_ERROR",
        details: Optional[dict[str, Any]] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        local_version: Optional[int] = None,
        remote_version: Optional[int] = None,
    ):
        self.local_version = local_version
        self.remote_version = remote_version
        super().__init__(message, code, details, entity_type, entity_id)


class IdempotencyError(QuickBooksSyncError):
    """Idempotency check failed."""

    def __init__(
        self,
        message: str = "Idempotency check failed",
        code: Optional[str] = "IDEMPOTENCY_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class WebhookError(QuickBooksSyncError):
    """Webhook processing error."""

    def __init__(
        self,
        message: str = "Webhook processing failed",
        code: Optional[str] = "WEBHOOK_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class ValidationError(QuickBooksSyncError):
    """Validation error."""

    def __init__(
        self,
        message: str = "Validation failed",
        code: Optional[str] = "VALIDATION_ERROR",
        details: Optional[dict[str, Any]] = None,
        field_errors: Optional[dict[str, list[str]]] = None,
    ):
        self.field_errors = field_errors or {}
        super().__init__(message, code, details)


class ConfigurationError(QuickBooksSyncError):
    """Configuration error."""

    def __init__(
        self,
        message: str = "Configuration error",
        code: Optional[str] = "CONFIGURATION_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class APIError(QuickBooksSyncError):
    """QuickBooks API error."""

    def __init__(
        self,
        message: str = "QuickBooks API error",
        code: Optional[str] = "API_ERROR",
        details: Optional[dict[str, Any]] = None,
        fault_code: Optional[str] = None,
        fault_type: Optional[str] = None,
    ):
        self.fault_code = fault_code
        self.fault_type = fault_type
        super().__init__(message, code, details)
