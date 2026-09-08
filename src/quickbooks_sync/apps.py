from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class QuickBooksSyncConfig(AppConfig):
    """Configuration for the quickbooks_sync app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "quickbooks_sync"
    verbose_name = _("QuickBooks Sync")
    default_settings = {
        "CLIENT_ID": "",
        "CLIENT_SECRET": "",
        "REDIRECT_URI": "",
        "ENVIRONMENT": "sandbox",  # 'sandbox' or 'production'
        "REALM_ID": "",
        "ACCESS_TOKEN": "",
        "REFRESH_TOKEN": "",
        "TOKEN_EXPIRES_AT": None,
        "SYNC_ENABLED": True,
        "WEBHOOK_ENABLED": False,
        "WEBHOOK_VERIFIER_TOKEN": "",
        "RATE_LIMIT_ENABLED": True,
        "MAX_REQUESTS_PER_MINUTE": 500,
        "MAX_CONCURRENT_REQUESTS": 10,
        "IDEMPOTENCY_KEY_ENABLED": True,
        "AUDIT_LOG_ENABLED": True,
        "CELERY_TASK_QUEUE": "quickbooks_sync",
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
        "CONFLICT_RESOLUTION": "last_write_wins",  # 'last_write_wins', 'manual', 'source_wins'
    }

    class Meta:
        app_label = "quickbooks_sync"
        verbose_name = _("QuickBooks Sync")
        verbose_name_plural = _("QuickBooks Sync")
