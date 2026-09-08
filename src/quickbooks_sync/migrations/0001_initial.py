import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="QuickBooksRealm",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "realm_id",
                    models.CharField(
                        help_text="QuickBooks Online company ID",
                        max_length=50,
                        unique=True,
                        verbose_name="Realm ID",
                    ),
                ),
                (
                    "company_name",
                    models.CharField(
                        blank=True,
                        help_text="Company name from QuickBooks",
                        max_length=255,
                        verbose_name="Company Name",
                    ),
                ),
                (
                    "access_token",
                    models.TextField(
                        help_text="OAuth access token (encrypted)",
                        verbose_name="Access Token",
                    ),
                ),
                (
                    "refresh_token",
                    models.TextField(
                        help_text="OAuth refresh token (encrypted)",
                        verbose_name="Refresh Token",
                    ),
                ),
                (
                    "token_expires_at",
                    models.DateTimeField(
                        help_text="When the access token expires",
                        verbose_name="Token Expires At",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this realm is active for sync",
                        verbose_name="Is Active",
                    ),
                ),
                (
                    "last_sync_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the last sync occurred",
                        null=True,
                        verbose_name="Last Sync At",
                    ),
                ),
                (
                    "sync_enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Whether sync is enabled for this realm",
                        verbose_name="Sync Enabled",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
            ],
            options={
                "verbose_name": "QuickBooks Realm",
                "verbose_name_plural": "QuickBooks Realms",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SyncLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "entity_type",
                    models.CharField(
                        help_text="QuickBooks entity type (e.g., Customer, Invoice)",
                        max_length=50,
                        verbose_name="Entity Type",
                    ),
                ),
                (
                    "entity_id",
                    models.CharField(
                        help_text="QuickBooks entity ID",
                        max_length=50,
                        verbose_name="Entity ID",
                    ),
                ),
                (
                    "direction",
                    models.CharField(
                        choices=[
                            ("to_qbo", "To QuickBooks"),
                            ("from_qbo", "From QuickBooks"),
                            ("bidirectional", "Bidirectional"),
                        ],
                        help_text="Sync direction",
                        max_length=20,
                        verbose_name="Direction",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                            ("retrying", "Retrying"),
                        ],
                        default="pending",
                        help_text="Sync status",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True,
                        help_text="Error message if sync failed",
                        verbose_name="Error Message",
                    ),
                ),
                (
                    "idempotency_key",
                    models.CharField(
                        help_text="Unique key for idempotency",
                        max_length=64,
                        unique=True,
                        verbose_name="Idempotency Key",
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Sync payload data",
                        verbose_name="Payload",
                    ),
                ),
                (
                    "response",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="API response data",
                        verbose_name="Response",
                    ),
                ),
                (
                    "retry_count",
                    models.IntegerField(
                        default=0,
                        help_text="Number of retry attempts",
                        verbose_name="Retry Count",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "realm",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sync_logs",
                        to="quickbooks_sync.quickbooksrealm",
                        verbose_name="Realm",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sync Log",
                "verbose_name_plural": "Sync Logs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["entity_type", "entity_id"],
                        name="quickbooks__entity__idx",
                    ),
                    models.Index(fields=["status"], name="quickbooks__status__idx"),
                    models.Index(
                        fields=["idempotency_key"],
                        name="quickbooks__idempot__idx",
                    ),
                    models.Index(
                        fields=["created_at"], name="quickbooks__created__idx"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="AuditEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "entity_type",
                    models.CharField(
                        help_text="QuickBooks entity type",
                        max_length=50,
                        verbose_name="Entity Type",
                    ),
                ),
                (
                    "entity_id",
                    models.CharField(
                        help_text="QuickBooks entity ID",
                        max_length=50,
                        verbose_name="Entity ID",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "Create"),
                            ("update", "update"),
                            ("delete", "Delete"),
                            ("void", "Void"),
                        ],
                        help_text="Action performed",
                        max_length=20,
                        verbose_name="Action",
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        default=dict,
                        help_text="Request payload",
                        verbose_name="Payload",
                    ),
                ),
                (
                    "outcome",
                    models.CharField(
                        choices=[
                            ("success", "Success"),
                            ("failed", "Failed"),
                        ],
                        help_text="Operation outcome",
                        max_length=20,
                        verbose_name="Outcome",
                    ),
                ),
                (
                    "error_details",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Error details if operation failed",
                        verbose_name="Error Details",
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        help_text="IP address of the user",
                        null=True,
                        verbose_name="IP Address",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(auto_now_add=True, verbose_name="Timestamp"),
                ),
                (
                    "realm",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_entries",
                        to="quickbooks_sync.quickbooksrealm",
                        verbose_name="Realm",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        help_text="IP address of the user",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="quickbooks_audit_entries",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Audit Entry",
                "verbose_name_plural": "Audit Entries",
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["entity_type", "entity_id"],
                        name="quickbooks__audit_e__idx",
                    ),
                    models.Index(fields=["action"], name="quickbooks__action__idx"),
                    models.Index(fields=["outcome"], name="quickbooks__outcome__idx"),
                    models.Index(fields=["timestamp"], name="quickbooks__timesta__idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="WebhookEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_id",
                    models.CharField(
                        help_text="Unique event identifier from QuickBooks",
                        max_length=100,
                        unique=True,
                        verbose_name="Event ID",
                    ),
                ),
                (
                    "entity_type",
                    models.CharField(
                        help_text="Entity type that changed",
                        max_length=50,
                        verbose_name="Entity Type",
                    ),
                ),
                (
                    "entity_id",
                    models.CharField(
                        help_text="Entity ID that changed",
                        max_length=50,
                        verbose_name="Entity ID",
                    ),
                ),
                (
                    "operation",
                    models.CharField(
                        choices=[
                            ("Create", "Create"),
                            ("Update", "Update"),
                            ("Delete", "Delete"),
                            ("Merge", "Merge"),
                            ("Void", "Void"),
                        ],
                        help_text="Operation type",
                        max_length=20,
                        verbose_name="Operation",
                    ),
                ),
                (
                    "last_updated",
                    models.DateTimeField(
                        help_text="When the entity was last updated in QuickBooks",
                        verbose_name="Last Updated",
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        default=dict,
                        help_text="Raw webhook payload",
                        verbose_name="Payload",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("received", "Received"),
                            ("processing", "Processing"),
                            ("processed", "Processed"),
                            ("failed", "Failed"),
                        ],
                        default="received",
                        help_text="Processing status",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True,
                        help_text="Error message if processing failed",
                        verbose_name="Error Message",
                    ),
                ),
                (
                    "processed_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the event was processed",
                        null=True,
                        verbose_name="Processed At",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "realm",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webhook_events",
                        to="quickbooks_sync.quickbooksrealm",
                        verbose_name="Realm",
                    ),
                ),
            ],
            options={
                "verbose_name": "Webhook Event",
                "verbose_name_plural": "Webhook Events",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["event_id"], name="quickbooks__event_i__idx"),
                    models.Index(
                        fields=["entity_type", "entity_id"],
                        name="quickbooks__webhook__idx",
                    ),
                    models.Index(
                        fields=["status"], name="quickbooks__webhook__status_idx"
                    ),
                ],
            },
        ),
    ]
