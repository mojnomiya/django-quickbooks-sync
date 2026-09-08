"""Django admin configuration for quickbooks_sync."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from quickbooks_sync.models import AuditEntry, QuickBooksRealm, SyncLog, WebhookEvent


@admin.register(QuickBooksRealm)
class QuickBooksRealmAdmin(admin.ModelAdmin):
    """Admin configuration for QuickBooksRealm model."""

    list_display = [
        "realm_id",
        "company_name",
        "is_active",
        "sync_enabled",
        "last_sync_at",
        "created_at",
    ]
    list_filter = ["is_active", "sync_enabled", "created_at"]
    search_fields = ["realm_id", "company_name"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (
            None,
            {
                "fields": ("realm_id", "company_name", "is_active", "sync_enabled"),
            },
        ),
        (
            _("Tokens"),
            {
                "fields": ("access_token", "refresh_token", "token_expires_at"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Status"),
            {
                "fields": ("last_sync_at", "created_at", "updated_at"),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ["realm_id"]
        return self.readonly_fields


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    """Admin configuration for SyncLog model."""

    list_display = [
        "id",
        "entity_type",
        "entity_id",
        "direction",
        "status",
        "retry_count",
        "created_at",
    ]
    list_filter = ["entity_type", "direction", "status", "created_at"]
    search_fields = ["entity_id", "idempotency_key", "error_message"]
    readonly_fields = [
        "realm",
        "entity_type",
        "entity_id",
        "direction",
        "idempotency_key",
        "payload",
        "response",
        "retry_count",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "realm",
                    "entity_type",
                    "entity_id",
                    "direction",
                    "status",
                ),
            },
        ),
        (
            _("Details"),
            {
                "fields": ("idempotency_key", "payload", "response"),
            },
        ),
        (
            _("Error Information"),
            {
                "fields": ("error_message", "retry_count"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    """Admin configuration for AuditEntry model."""

    list_display = [
        "id",
        "entity_type",
        "entity_id",
        "action",
        "outcome",
        "user",
        "timestamp",
    ]
    list_filter = ["entity_type", "action", "outcome", "timestamp"]
    search_fields = ["entity_id", "user__username", "ip_address"]
    readonly_fields = [
        "realm",
        "entity_type",
        "entity_id",
        "action",
        "payload",
        "outcome",
        "error_details",
        "user",
        "ip_address",
        "timestamp",
    ]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "realm",
                    "entity_type",
                    "entity_id",
                    "action",
                    "outcome",
                ),
            },
        ),
        (
            _("Request Details"),
            {
                "fields": ("payload", "user", "ip_address"),
            },
        ),
        (
            _("Error Information"),
            {
                "fields": ("error_details",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamp"),
            {
                "fields": ("timestamp",),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    """Admin configuration for WebhookEvent model."""

    list_display = [
        "id",
        "event_id",
        "entity_type",
        "entity_id",
        "operation",
        "status",
        "created_at",
    ]
    list_filter = ["entity_type", "operation", "status", "created_at"]
    search_fields = ["event_id", "entity_id", "error_message"]
    readonly_fields = [
        "realm",
        "event_id",
        "entity_type",
        "entity_id",
        "operation",
        "last_updated",
        "payload",
        "status",
        "error_message",
        "processed_at",
        "created_at",
    ]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "realm",
                    "event_id",
                    "entity_type",
                    "entity_id",
                    "operation",
                    "last_updated",
                ),
            },
        ),
        (
            _("Payload"),
            {
                "fields": ("payload",),
            },
        ),
        (
            _("Processing"),
            {
                "fields": ("status", "error_message", "processed_at"),
            },
        ),
        (
            _("Timestamp"),
            {
                "fields": ("created_at",),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
