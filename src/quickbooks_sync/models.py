"""Django models for quickbooks_sync."""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class QuickBooksRealm(models.Model):
    """
    Stores QuickBooks Online company/realm information.

    Each realm represents a connected QuickBooks Online company
    with its own OAuth tokens and sync state.
    """

    realm_id = models.CharField(
        _("Realm ID"),
        max_length=50,
        unique=True,
        help_text=_("QuickBooks Online company ID"),
    )
    company_name = models.CharField(
        _("Company Name"),
        max_length=255,
        blank=True,
        help_text=_("Company name from QuickBooks"),
    )
    access_token = models.TextField(
        _("Access Token"),
        help_text=_("OAuth access token (encrypted)"),
    )
    refresh_token = models.TextField(
        _("Refresh Token"),
        help_text=_("OAuth refresh token (encrypted)"),
    )
    token_expires_at = models.DateTimeField(
        _("Token Expires At"),
        help_text=_("When the access token expires"),
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this realm is active for sync"),
    )
    last_sync_at = models.DateTimeField(
        _("Last Sync At"),
        null=True,
        blank=True,
        help_text=_("When the last sync occurred"),
    )
    sync_enabled = models.BooleanField(
        _("Sync Enabled"),
        default=True,
        help_text=_("Whether sync is enabled for this realm"),
    )
    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("Updated At"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("QuickBooks Realm")
        verbose_name_plural = _("QuickBooks Realms")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.company_name} ({self.realm_id})"

    @property
    def is_token_expired(self) -> bool:
        """Check if the access token is expired or about to expire."""
        if self.token_expires_at is None:
            return True
        # Check if token expires within 5 minutes
        return timezone.now() >= (self.token_expires_at - timezone.timedelta(minutes=5))

    @property
    def environment(self) -> str:
        """Get the environment (sandbox/production) for this realm."""
        from quickbooks_sync.settings import qbs_settings

        return qbs_settings.ENVIRONMENT


class SyncLog(models.Model):
    """
    Tracks sync operations between Django and QuickBooks.

    Each sync operation creates a log entry for tracking
    and debugging purposes.
    """

    class Direction(models.TextChoices):
        TO_QBO = "to_qbo", _("To QuickBooks")
        FROM_QBO = "from_qbo", _("From QuickBooks")
        BIDIRECTIONAL = "bidirectional", _("Bidirectional")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        IN_PROGRESS = "in_progress", _("In Progress")
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")
        RETRYING = "retrying", _("Retrying")

    realm = models.ForeignKey(
        QuickBooksRealm,
        on_delete=models.CASCADE,
        related_name="sync_logs",
        verbose_name=_("Realm"),
    )
    entity_type = models.CharField(
        _("Entity Type"),
        max_length=50,
        help_text=_("QuickBooks entity type (e.g., Customer, Invoice)"),
    )
    entity_id = models.CharField(
        _("Entity ID"),
        max_length=50,
        help_text=_("QuickBooks entity ID"),
    )
    direction = models.CharField(
        _("Direction"),
        max_length=20,
        choices=Direction.choices,
        help_text=_("Sync direction"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_("Sync status"),
    )
    error_message = models.TextField(
        _("Error Message"),
        blank=True,
        help_text=_("Error message if sync failed"),
    )
    idempotency_key = models.CharField(
        _("Idempotency Key"),
        max_length=64,
        unique=True,
        help_text=_("Unique key for idempotency"),
    )
    payload = models.JSONField(
        _("Payload"),
        default=dict,
        blank=True,
        help_text=_("Sync payload data"),
    )
    response = models.JSONField(
        _("Response"),
        default=dict,
        blank=True,
        help_text=_("API response data"),
    )
    retry_count = models.IntegerField(
        _("Retry Count"),
        default=0,
        help_text=_("Number of retry attempts"),
    )
    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("Updated At"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("Sync Log")
        verbose_name_plural = _("Sync Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["idempotency_key"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.entity_type}:{self.entity_id} - "
            f"{self.get_direction_display()} - "
            f"{self.get_status_display()}"
        )


class AuditEntry(models.Model):
    """
    Audit trail for every API write operation.

    Records all create, update, and delete operations
    for compliance and debugging purposes.
    """

    class Action(models.TextChoices):
        CREATE = "create", _("Create")
        UPDATE = "update", _("Update")
        DELETE = "delete", _("Delete")
        VOID = "void", _("Void")

    realm = models.ForeignKey(
        QuickBooksRealm,
        on_delete=models.CASCADE,
        related_name="audit_entries",
        verbose_name=_("Realm"),
    )
    entity_type = models.CharField(
        _("Entity Type"),
        max_length=50,
        help_text=_("QuickBooks entity type"),
    )
    entity_id = models.CharField(
        _("Entity ID"),
        max_length=50,
        help_text=_("QuickBooks entity ID"),
    )
    action = models.CharField(
        _("Action"),
        max_length=20,
        choices=Action.choices,
        help_text=_("Action performed"),
    )
    payload = models.JSONField(
        _("Payload"),
        default=dict,
        help_text=_("Request payload"),
    )
    outcome = models.CharField(
        _("Outcome"),
        max_length=20,
        choices=[
            ("success", _("Success")),
            ("failed", _("Failed")),
        ],
        help_text=_("Operation outcome"),
    )
    error_details = models.JSONField(
        _("Error Details"),
        default=dict,
        blank=True,
        help_text=_("Error details if operation failed"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quickbooks_audit_entries",
        verbose_name=_("User"),
    )
    ip_address = models.GenericIPAddressField(
        _("IP Address"),
        null=True,
        blank=True,
        help_text=_("IP address of the user"),
    )
    timestamp = models.DateTimeField(
        _("Timestamp"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("Audit Entry")
        verbose_name_plural = _("Audit Entries")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["outcome"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_action_display()} {self.entity_type}:{self.entity_id} - "
            f"{self.outcome}"
        )


class WebhookEvent(models.Model):
    """
    Stores incoming webhook events from QuickBooks.

    Used for idempotent processing of webhook notifications.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", _("Received")
        PROCESSING = "processing", _("Processing")
        PROCESSED = "processed", _("Processed")
        FAILED = "failed", _("Failed")

    realm = models.ForeignKey(
        QuickBooksRealm,
        on_delete=models.CASCADE,
        related_name="webhook_events",
        verbose_name=_("Realm"),
    )
    event_id = models.CharField(
        _("Event ID"),
        max_length=100,
        unique=True,
        help_text=_("Unique event identifier from QuickBooks"),
    )
    entity_type = models.CharField(
        _("Entity Type"),
        max_length=50,
        help_text=_("Entity type that changed"),
    )
    entity_id = models.CharField(
        _("Entity ID"),
        max_length=50,
        help_text=_("Entity ID that changed"),
    )
    operation = models.CharField(
        _("Operation"),
        max_length=20,
        choices=[
            ("Create", _("Create")),
            ("Update", _("Update")),
            ("Delete", _("Delete")),
            ("Merge", _("Merge")),
            ("Void", _("Void")),
        ],
        help_text=_("Operation type"),
    )
    last_updated = models.DateTimeField(
        _("Last Updated"),
        help_text=_("When the entity was last updated in QuickBooks"),
    )
    payload = models.JSONField(
        _("Payload"),
        default=dict,
        help_text=_("Raw webhook payload"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
        help_text=_("Processing status"),
    )
    error_message = models.TextField(
        _("Error Message"),
        blank=True,
        help_text=_("Error message if processing failed"),
    )
    processed_at = models.DateTimeField(
        _("Processed At"),
        null=True,
        blank=True,
        help_text=_("When the event was processed"),
    )
    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("Webhook Event")
        verbose_name_plural = _("Webhook Events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_id"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.operation} {self.entity_type}:{self.entity_id} - {self.get_status_display()}"
