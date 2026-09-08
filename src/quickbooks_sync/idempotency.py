"""Idempotency handling for QuickBooks API."""

import time
from typing import Optional

from django.db import IntegrityError
from django.utils import timezone

from quickbooks_sync.exceptions import IdempotencyError
from quickbooks_sync.models import SyncLog
from quickbooks_sync.settings import qbs_settings
from quickbooks_sync.utils import generate_idempotency_key


class IdempotencyManager:
    """
    Manages idempotency for sync operations.

    Ensures that the same operation is not performed multiple times,
    even if the request is retried.
    """

    # Idempotency key validity period (24 hours)
    KEY_VALIDITY_SECONDS = 24 * 60 * 60

    def __init__(self, enabled: Optional[bool] = None):
        """
        Initialize the idempotency manager.

        Args:
            enabled: Whether idempotency is enabled
        """
        self.enabled = (
            enabled if enabled is not None else qbs_settings.IDEMPOTENCY_KEY_ENABLED
        )

    def generate_key(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        timestamp: Optional[timezone.datetime] = None,
    ) -> str:
        """
        Generate an idempotency key.

        Args:
            entity_type: The type of entity
            entity_id: The ID of the entity
            action: The action being performed
            timestamp: Optional timestamp for uniqueness

        Returns:
            Generated idempotency key
        """
        return generate_idempotency_key(entity_type, entity_id, action, timestamp)

    def check_key(self, idempotency_key: str) -> Optional[SyncLog]:
        """
        Check if an idempotency key already exists.

        Args:
            idempotency_key: The key to check

        Returns:
            Existing SyncLog if key exists, None otherwise
        """
        if not self.enabled:
            return None

        try:
            sync_log = SyncLog.objects.get(idempotency_key=idempotency_key)

            # Check if the key is still valid
            age = (timezone.now() - sync_log.created_at).total_seconds()
            if age > self.KEY_VALIDITY_SECONDS:
                # Key has expired, allow reprocessing
                return None

            return sync_log
        except SyncLog.DoesNotExist:
            return None

    def create_log(
        self,
        realm_id: int,
        entity_type: str,
        entity_id: str,
        direction: str,
        idempotency_key: str,
        payload: Optional[dict] = None,
    ) -> SyncLog:
        """
        Create a new sync log entry.

        Args:
            realm_id: The realm ID
            entity_type: The entity type
            entity_id: The entity ID
            direction: Sync direction
            idempotency_key: The idempotency key
            payload: Optional payload data

        Returns:
            Created SyncLog

        Raises:
            IdempotencyError: If key already exists
        """
        if not self.enabled:
            # If idempotency is disabled, generate a unique key
            idempotency_key = self.generate_key(
                entity_type, entity_id, f"{direction}:{time.time()}"
            )

        try:
            sync_log = SyncLog.objects.create(
                realm_id=realm_id,
                entity_type=entity_type,
                entity_id=entity_id,
                direction=direction,
                idempotency_key=idempotency_key,
                payload=payload or {},
                status=SyncLog.Status.PENDING,
            )
            return sync_log
        except IntegrityError:
            raise IdempotencyError(
                f"Idempotency key already exists: {idempotency_key}",
                details={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "direction": direction,
                },
            )

    def update_log(
        self,
        sync_log: SyncLog,
        status: str,
        response: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> SyncLog:
        """
        Update a sync log entry.

        Args:
            sync_log: The sync log to update
            status: New status
            response: Optional response data
            error_message: Optional error message

        Returns:
            Updated SyncLog
        """
        sync_log.status = status
        if response is not None:
            sync_log.response = response
        if error_message is not None:
            sync_log.error_message = error_message
        sync_log.save()

        return sync_log

    def get_completed_operations(self, hours: int = 24) -> list[dict]:
        """
        Get completed operations within the specified time window.

        Args:
            hours: Number of hours to look back

        Returns:
            List of completed operation details
        """
        cutoff = timezone.now() - timezone.timedelta(hours=hours)

        return list(
            SyncLog.objects.filter(
                created_at__gte=cutoff,
                status=SyncLog.Status.SUCCESS,
            ).values(
                "entity_type",
                "entity_id",
                "direction",
                "idempotency_key",
                "created_at",
            )
        )

    def cleanup_expired_keys(self, days: int = 7) -> int:
        """
        Clean up expired idempotency keys.

        Args:
            days: Number of days to keep keys

        Returns:
            Number of deleted entries
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)

        deleted_count, _ = SyncLog.objects.filter(
            created_at__lt=cutoff,
        ).delete()

        return deleted_count


# Global idempotency manager instance
idempotency_manager = IdempotencyManager()
