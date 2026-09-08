"""Settings for quickbooks_sync."""

from django.conf import settings
from django.test import TestCase

# Default settings
DEFAULT_SETTINGS = {
    # OAuth Settings
    "CLIENT_ID": "",
    "CLIENT_SECRET": "",
    "REDIRECT_URI": "",
    "ENVIRONMENT": "sandbox",  # 'sandbox' or 'production'
    # Token Settings
    "REALM_ID": "",
    "ACCESS_TOKEN": "",
    "REFRESH_TOKEN": "",
    "TOKEN_EXPIRES_AT": None,
    # Sync Settings
    "SYNC_ENABLED": True,
    "WEBHOOK_ENABLED": False,
    "WEBHOOK_VERIFIER_TOKEN": "",
    # Rate Limiting
    "RATE_LIMIT_ENABLED": True,
    "MAX_REQUESTS_PER_MINUTE": 500,
    "MAX_CONCURRENT_REQUESTS": 10,
    # Idempotency
    "IDEMPOTENCY_KEY_ENABLED": True,
    # Audit Logging
    "AUDIT_LOG_ENABLED": True,
    # Celery
    "CELERY_TASK_QUEUE": "quickbooks_sync",
    # Entity Sync
    "SYNC_ENTITIES": [
        "Account",
        "Customer",
        "Vendor",
        "Invoice",
        "Bill",
        "Payment",
        "Item",
        "Employee",
    ],
    # Conflict Resolution
    "CONFLICT_RESOLUTION": "last_write_wins",  # 'last_write_wins', 'manual', 'source_wins'
}


class QuickBooksSyncSettings:
    """
    A class to access quickbooks_sync settings.

    Settings are accessed via attributes, with fallback to defaults.
    Example:
        from quickbooks_sync.settings import qbs_settings
        client_id = qbs_settings.CLIENT_ID
    """

    def __getattr__(self, name: str):
        if name not in DEFAULT_SETTINGS:
            raise AttributeError(f"Invalid quickbooks_sync setting: '{name}'")

        default_value = DEFAULT_SETTINGS[name]
        return getattr(settings, f"QUICKBOOKS_SYNC_{name}", default_value)


# Singleton instance
qbs_settings = QuickBooksSyncSettings()


def get_settings() -> dict:
    """Get all quickbooks_sync settings as a dictionary."""
    return {key: getattr(qbs_settings, key) for key in DEFAULT_SETTINGS}


def validate_settings() -> list[str]:
    """
    Validate quickbooks_sync settings.

    Returns a list of error messages. Empty list means all settings are valid.
    """
    errors = []

    if not qbs_settings.CLIENT_ID:
        errors.append("QUICKBOOKS_SYNC_CLIENT_ID is required")
    if not qbs_settings.CLIENT_SECRET:
        errors.append("QUICKBOOKS_SYNC_CLIENT_SECRET is required")
    if not qbs_settings.REDIRECT_URI:
        errors.append("QUICKBOOKS_SYNC_REDIRECT_URI is required")

    if qbs_settings.ENVIRONMENT not in ("sandbox", "production"):
        errors.append(
            f"QUICKBOOKS_SYNC_ENVIRONMENT must be 'sandbox' or 'production', "
            f"got '{qbs_settings.ENVIRONMENT}'"
        )

    if qbs_settings.MAX_REQUESTS_PER_MINUTE < 1:
        errors.append("QUICKBOOKS_SYNC_MAX_REQUESTS_PER_MINUTE must be at least 1")

    if qbs_settings.MAX_CONCURRENT_REQUESTS < 1:
        errors.append("QUICKBOOKS_SYNC_MAX_CONCURRENT_REQUESTS must be at least 1")

    if qbs_settings.CONFLICT_RESOLUTION not in (
        "last_write_wins",
        "manual",
        "source_wins",
    ):
        errors.append(
            f"QUICKBOOKS_SYNC_CONFLICT_RESOLUTION must be 'last_write_wins', "
            f"'manual', or 'source_wins', got '{qbs_settings.CONFLICT_RESOLUTION}'"
        )

    return errors
