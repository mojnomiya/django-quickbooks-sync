"""Core sync engine for QuickBooks integration."""

from typing import Any, Optional

from django.utils import timezone

from quickbooks_sync.client import QuickBooksClient
from quickbooks_sync.exceptions import ConflictError, SyncError
from quickbooks_sync.idempotency import idempotency_manager
from quickbooks_sync.models import AuditEntry, QuickBooksRealm, SyncLog
from quickbooks_sync.rate_limiter import per_realm_rate_limiter
from quickbooks_sync.settings import qbs_settings
from quickbooks_sync.utils import parse_qbo_datetime


class SyncEngine:
    """
    Core bidirectional sync engine for QuickBooks Online.

    Handles synchronization between Django and QuickBooks,
    including conflict resolution and audit logging.
    """

    def __init__(self, realm: QuickBooksRealm):
        """
        Initialize the sync engine.

        Args:
            realm: The QuickBooks realm to sync with
        """
        self.realm = realm
        self.client = QuickBooksClient(
            access_token=realm.access_token,
            refresh_token=realm.refresh_token,
            realm_id=realm.realm_id,
        )

    def sync_to_qbo(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: dict,
        user: Optional[Any] = None,
    ) -> SyncLog:
        """
        Push local changes to QuickBooks.

        Args:
            entity_type: QuickBooks entity type (e.g., 'Customer')
            entity_id: Local entity ID
            entity_data: Entity data to sync
            user: Optional user performing the sync

        Returns:
            SyncLog entry for this operation
        """
        # Generate idempotency key
        idempotency_key = idempotency_manager.generate_key(
            entity_type, entity_id, "create"
        )

        # Check for existing operation
        existing_log = idempotency_manager.check_key(idempotency_key)
        if existing_log and existing_log.status == SyncLog.Status.SUCCESS:
            return existing_log

        # Create sync log
        sync_log = idempotency_manager.create_log(
            realm_id=self.realm.id,
            entity_type=entity_type,
            entity_id=entity_id,
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key=idempotency_key,
            payload=entity_data,
        )

        try:
            # Acquire rate limit slot
            per_realm_rate_limiter.acquire(self.realm.realm_id)

            # Perform the API call
            sync_log.status = SyncLog.Status.IN_PROGRESS
            sync_log.save()

            # Check if entity exists in QBO
            try:
                self.client.get_entity(entity_type, entity_id)
                # Update existing entity
                result = self.client.update_entity(entity_type, entity_id, entity_data)
                action = AuditEntry.Action.UPDATE
            except Exception:
                # Create new entity
                result = self.client.create_entity(entity_type, entity_data)
                action = AuditEntry.Action.CREATE
                entity_id = str(result.id)

            # Update sync log
            idempotency_manager.update_log(
                sync_log,
                status=SyncLog.Status.SUCCESS,
                response={"id": str(result.id)},
            )

            # Create audit entry
            self._create_audit_entry(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                payload=entity_data,
                outcome="success",
                user=user,
            )

            # Update realm last sync time
            self.realm.last_sync_at = timezone.now()
            self.realm.save(update_fields=["last_sync_at"])

            return sync_log

        except ConflictError as e:
            # Handle conflict based on resolution strategy
            return self._handle_conflict(
                sync_log, entity_type, entity_id, entity_data, e, user
            )

        except Exception as e:
            # Update sync log with error
            idempotency_manager.update_log(
                sync_log,
                status=SyncLog.Status.FAILED,
                error_message=str(e),
            )

            # Create audit entry for failure
            self._create_audit_entry(
                entity_type=entity_type,
                entity_id=entity_id,
                action=AuditEntry.Action.CREATE,
                payload=entity_data,
                outcome="failed",
                error_details={"error": str(e)},
                user=user,
            )

            raise SyncError(
                f"Failed to sync {entity_type} to QBO: {str(e)}",
                entity_type=entity_type,
                entity_id=entity_id,
            )

        finally:
            # Release rate limit slot
            per_realm_rate_limiter.release(self.realm.realm_id)

    def sync_from_qbo(
        self,
        entity_type: str,
        entity_id: str,
        user: Optional[Any] = None,
    ) -> dict:
        """
        Pull changes from QuickBooks.

        Args:
            entity_type: QuickBooks entity type
            entity_id: QuickBooks entity ID
            user: Optional user performing the sync

        Returns:
            Entity data from QuickBooks
        """
        # Generate idempotency key
        idempotency_key = idempotency_manager.generate_key(
            entity_type, entity_id, "fetch"
        )

        # Check for existing operation
        existing_log = idempotency_manager.check_key(idempotency_key)
        if existing_log and existing_log.status == SyncLog.Status.SUCCESS:
            return existing_log.response

        # Create sync log
        sync_log = idempotency_manager.create_log(
            realm_id=self.realm.id,
            entity_type=entity_type,
            entity_id=entity_id,
            direction=SyncLog.Direction.FROM_QBO,
            idempotency_key=idempotency_key,
        )

        try:
            # Acquire rate limit slot
            per_realm_rate_limiter.acquire(self.realm.realm_id)

            # Perform the API call
            sync_log.status = SyncLog.Status.IN_PROGRESS
            sync_log.save()

            qbo_entity = self.client.get_entity(entity_type, entity_id)

            # Convert entity to dictionary
            entity_data = self._entity_to_dict(qbo_entity)

            # Update sync log
            idempotency_manager.update_log(
                sync_log,
                status=SyncLog.Status.SUCCESS,
                response=entity_data,
            )

            # Create audit entry
            self._create_audit_entry(
                entity_type=entity_type,
                entity_id=entity_id,
                action=AuditEntry.Action.UPDATE,
                payload=entity_data,
                outcome="success",
                user=user,
            )

            # Update realm last sync time
            self.realm.last_sync_at = timezone.now()
            self.realm.save(update_fields=["last_sync_at"])

            return entity_data

        except Exception as e:
            # Update sync log with error
            idempotency_manager.update_log(
                sync_log,
                status=SyncLog.Status.FAILED,
                error_message=str(e),
            )

            raise SyncError(
                f"Failed to sync {entity_type} from QBO: {str(e)}",
                entity_type=entity_type,
                entity_id=entity_id,
            )

        finally:
            # Release rate limit slot
            per_realm_rate_limiter.release(self.realm.realm_id)

    def full_sync(
        self,
        entity_types: Optional[list[str]] = None,
        user: Optional[Any] = None,
    ) -> dict:
        """
        Perform a full bidirectional sync.

        Args:
            entity_types: List of entity types to sync (default: all)
            user: Optional user performing the sync

        Returns:
            Dictionary with sync results
        """
        if entity_types is None:
            entity_types = qbs_settings.SYNC_ENTITIES

        results = {
            "synced": {},
            "errors": {},
            "total": 0,
            "success": 0,
            "failed": 0,
        }

        # Sync order matters due to dependencies
        sync_order = [
            "Account",
            "Customer",
            "Vendor",
            "Employee",
            "Item",
            "Invoice",
            "Bill",
            "Payment",
        ]

        # Filter and order entity types
        ordered_types = [t for t in sync_order if t in entity_types]
        # Add any remaining types not in the order
        ordered_types.extend([t for t in entity_types if t not in ordered_types])

        for entity_type in ordered_types:
            try:
                # Sync from QBO to Django
                entities = self._sync_entity_type_from_qbo(entity_type, user)
                results["synced"][entity_type] = len(entities)
                results["total"] += len(entities)
                results["success"] += len(entities)

            except Exception as e:
                results["errors"][entity_type] = str(e)
                results["failed"] += 1

        return results

    def _sync_entity_type_from_qbo(
        self,
        entity_type: str,
        user: Optional[Any] = None,
    ) -> list[dict]:
        """
        Sync all entities of a specific type from QBO.

        Args:
            entity_type: Entity type to sync
            user: Optional user performing the sync

        Returns:
            List of synced entity data
        """
        synced_entities = []
        start_position = 1
        max_results = 1000

        while True:
            # Query entities from QBO
            entities = self.client.query_entities(
                entity_type=entity_type,
                max_results=max_results,
                start_position=start_position,
            )

            if not entities:
                break

            for entity in entities:
                entity_data = self._entity_to_dict(entity)
                entity_id = str(entity.id)

                # Generate idempotency key
                idempotency_key = idempotency_manager.generate_key(
                    entity_type, entity_id, "fetch"
                )

                # Check if already synced recently
                existing_log = idempotency_manager.check_key(idempotency_key)
                if existing_log and existing_log.status == SyncLog.Status.SUCCESS:
                    continue

                # Create sync log and store the data
                sync_log = idempotency_manager.create_log(
                    realm_id=self.realm.id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    direction=SyncLog.Direction.FROM_QBO,
                    idempotency_key=idempotency_key,
                    payload=entity_data,
                )

                # Mark as successful
                idempotency_manager.update_log(
                    sync_log,
                    status=SyncLog.Status.SUCCESS,
                    response=entity_data,
                )

                synced_entities.append(entity_data)

            # Check if we've fetched all entities
            if len(entities) < max_results:
                break

            start_position += max_results

        return synced_entities

    def _entity_to_dict(self, entity: Any) -> dict:
        """
        Convert a QuickBooks entity to a dictionary.

        Args:
            entity: QuickBooks entity object

        Returns:
            Dictionary representation
        """
        if hasattr(entity, "to_dict"):
            return entity.to_dict()

        # Fallback to converting attributes
        result = {}
        for attr in dir(entity):
            if not attr.startswith("_") and not callable(getattr(entity, attr)):
                value = getattr(entity, attr)
                if not callable(value):
                    result[attr] = value

        return result

    def _handle_conflict(
        self,
        sync_log: SyncLog,
        entity_type: str,
        entity_id: str,
        entity_data: dict,
        conflict: ConflictError,
        user: Optional[Any] = None,
    ) -> SyncLog:
        """
        Handle sync conflicts based on resolution strategy.

        Args:
            sync_log: The sync log entry
            entity_type: Entity type
            entity_id: Entity ID
            entity_data: Local entity data
            conflict: The conflict error
            user: Optional user

        Returns:
            Updated SyncLog
        """
        strategy = qbs_settings.CONFLICT_RESOLUTION

        if strategy == "source_wins":
            # Local data wins, push to QBO
            try:
                result = self.client.update_entity(entity_type, entity_id, entity_data)
                idempotency_manager.update_log(
                    sync_log,
                    status=SyncLog.Status.SUCCESS,
                    response={"id": str(result.id), "resolution": "source_wins"},
                )
                return sync_log
            except Exception as e:
                idempotency_manager.update_log(
                    sync_log,
                    status=SyncLog.Status.FAILED,
                    error_message=f"Conflict resolution failed: {str(e)}",
                )
                raise

        elif strategy == "last_write_wins":
            # Fetch remote data and compare timestamps
            try:
                remote_data = self.sync_from_qbo(entity_type, entity_id, user)
                remote_updated = parse_qbo_datetime(
                    remote_data.get("MetaData", {}).get("LastUpdatedTime", "")
                )
                local_updated = entity_data.get("updated_at", timezone.now())

                if remote_updated > local_updated:
                    # Remote is newer, use remote data
                    idempotency_manager.update_log(
                        sync_log,
                        status=SyncLog.Status.SUCCESS,
                        response={
                            "resolution": "last_write_wins",
                            "winner": "remote",
                        },
                    )
                else:
                    # Local is newer, push to QBO
                    result = self.client.update_entity(
                        entity_type, entity_id, entity_data
                    )
                    idempotency_manager.update_log(
                        sync_log,
                        status=SyncLog.Status.SUCCESS,
                        response={
                            "id": str(result.id),
                            "resolution": "last_write_wins",
                            "winner": "local",
                        },
                    )
                return sync_log

            except Exception as e:
                idempotency_manager.update_log(
                    sync_log,
                    status=SyncLog.Status.FAILED,
                    error_message=f"Conflict resolution failed: {str(e)}",
                )
                raise

        else:
            # Manual resolution - mark as failed for manual intervention
            idempotency_manager.update_log(
                sync_log,
                status=SyncLog.Status.FAILED,
                error_message="Conflict requires manual resolution",
            )
            return sync_log

    def _create_audit_entry(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        payload: dict,
        outcome: str,
        user: Optional[Any] = None,
        error_details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditEntry:
        """
        Create an audit entry.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            action: Action performed
            payload: Request payload
            outcome: Operation outcome
            user: Optional user
            error_details: Optional error details
            ip_address: Optional IP address

        Returns:
            Created AuditEntry
        """
        if not qbs_settings.AUDIT_LOG_ENABLED:
            return None

        return AuditEntry.objects.create(
            realm=self.realm,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            payload=payload,
            outcome=outcome,
            error_details=error_details or {},
            user=user,
            ip_address=ip_address,
        )
