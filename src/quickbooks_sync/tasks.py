"""Celery tasks for QuickBooks sync."""

import logging
from typing import Optional

from celery import shared_task
from django.utils import timezone

from quickbooks_sync.client import QuickBooksClient
from quickbooks_sync.exceptions import OAuthError, SyncError
from quickbooks_sync.models import QuickBooksRealm
from quickbooks_sync.sync_engine import SyncEngine

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="quickbooks_sync.sync_entity",
    max_retries=3,
    default_retry_delay=60,
    queue="quickbooks_sync",
)
def sync_entity(
    self,
    realm_id: int,
    entity_type: str,
    entity_id: str,
    direction: str = "to_qbo",
    entity_data: Optional[dict] = None,
) -> dict:
    """
    Sync a single entity with QuickBooks.

    Args:
        realm_id: QuickBooksRealm ID
        entity_type: Entity type (e.g., 'Customer', 'Invoice')
        entity_id: Entity ID
        direction: 'to_qbo' or 'from_qbo'
        entity_data: Entity data (required for 'to_qbo')

    Returns:
        Dictionary with sync result
    """
    try:
        realm = QuickBooksRealm.objects.get(id=realm_id, is_active=True)
    except QuickBooksRealm.DoesNotExist:
        logger.error(f"Realm {realm_id} not found or inactive")
        return {"error": f"Realm {realm_id} not found or inactive"}

    try:
        engine = SyncEngine(realm)

        if direction == "to_qbo":
            if entity_data is None:
                return {"error": "entity_data is required for to_qbo sync"}

            engine.sync_to_qbo(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_data=entity_data,
            )
        else:
            entity_data = engine.sync_from_qbo(
                entity_type=entity_type,
                entity_id=entity_id,
            )

        return {
            "status": "success",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "direction": direction,
        }

    except OAuthError as e:
        logger.error(f"OAuth error syncing {entity_type}:{entity_id}: {str(e)}")
        # Don't retry OAuth errors - they need manual intervention
        return {
            "status": "error",
            "error": str(e),
            "error_type": "oauth",
        }

    except SyncError as e:
        logger.warning(f"Sync error for {entity_type}:{entity_id}, retrying: {str(e)}")
        raise self.retry(exc=e)

    except Exception as e:
        logger.error(f"Unexpected error syncing {entity_type}:{entity_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name="quickbooks_sync.full_sync",
    max_retries=1,
    default_retry_delay=300,
    queue="quickbooks_sync",
)
def full_sync(
    self,
    realm_id: int,
    entity_types: Optional[list[str]] = None,
) -> dict:
    """
    Perform a full sync for a realm.

    Args:
        realm_id: QuickBooksRealm ID
        entity_types: Optional list of entity types to sync

    Returns:
        Dictionary with sync results
    """
    try:
        realm = QuickBooksRealm.objects.get(id=realm_id, is_active=True)
    except QuickBooksRealm.DoesNotExist:
        logger.error(f"Realm {realm_id} not found or inactive")
        return {"error": f"Realm {realm_id} not found or inactive"}

    try:
        engine = SyncEngine(realm)
        results = engine.full_sync(entity_types=entity_types)

        return {
            "status": "success",
            "realm_id": realm_id,
            "results": results,
        }

    except OAuthError as e:
        logger.error(f"OAuth error during full sync for realm {realm_id}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": "oauth",
        }

    except Exception as e:
        logger.error(
            f"Unexpected error during full sync for realm {realm_id}: {str(e)}"
        )
        raise self.retry(exc=e)


@shared_task(
    name="quickbooks_sync.refresh_token",
    queue="quickbooks_sync",
)
def refresh_token(realm_id: int) -> dict:
    """
    Refresh the OAuth token for a realm.

    Args:
        realm_id: QuickBooksRealm ID

    Returns:
        Dictionary with refresh result
    """
    try:
        realm = QuickBooksRealm.objects.get(id=realm_id, is_active=True)
    except QuickBooksRealm.DoesNotExist:
        logger.error(f"Realm {realm_id} not found or inactive")
        return {"error": f"Realm {realm_id} not found or inactive"}

    try:
        client = QuickBooksClient(
            access_token=realm.access_token,
            refresh_token=realm.refresh_token,
            realm_id=realm.realm_id,
        )

        token_data = client.refresh_access_token()

        # Update realm with new tokens
        realm.access_token = token_data["access_token"]
        realm.refresh_token = token_data["refresh_token"]
        realm.token_expires_at = timezone.now() + timezone.timedelta(
            seconds=token_data.get("expires_in", 3600)
        )
        realm.save(update_fields=["access_token", "refresh_token", "token_expires_at"])

        logger.info(f"Successfully refreshed token for realm {realm_id}")

        return {
            "status": "success",
            "realm_id": realm_id,
            "expires_in": token_data.get("expires_in"),
        }

    except OAuthError as e:
        logger.error(f"Failed to refresh token for realm {realm_id}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": "oauth",
        }

    except Exception as e:
        logger.error(
            f"Unexpected error refreshing token for realm {realm_id}: {str(e)}"
        )
        return {
            "status": "error",
            "error": str(e),
            "error_type": "unknown",
        }


@shared_task(
    name="quickbooks_sync.process_webhook",
    queue="quickbooks_sync",
)
def process_webhook(
    realm_id: int,
    event_id: str,
    entity_type: str,
    entity_id: str,
    operation: str,
    last_updated: str,
) -> dict:
    """
    Process a webhook event from QuickBooks.

    Args:
        realm_id: QuickBooksRealm ID
        event_id: Unique event identifier
        entity_type: Entity type that changed
        entity_id: Entity ID that changed
        operation: Operation type (Create, Update, Delete)
        last_updated: When the entity was last updated

    Returns:
        Dictionary with processing result
    """
    from quickbooks_sync.models import WebhookEvent

    try:
        realm = QuickBooksRealm.objects.get(id=realm_id, is_active=True)
    except QuickBooksRealm.DoesNotExist:
        logger.error(f"Realm {realm_id} not found or inactive")
        return {"error": f"Realm {realm_id} not found or inactive"}

    # Check for duplicate event
    if WebhookEvent.objects.filter(event_id=event_id).exists():
        logger.info(f"Webhook event {event_id} already processed, skipping")
        return {"status": "skipped", "reason": "duplicate"}

    # Create webhook event record
    webhook_event = WebhookEvent.objects.create(
        realm=realm,
        event_id=event_id,
        entity_type=entity_type,
        entity_id=entity_id,
        operation=operation,
        last_updated=timezone.datetime.fromisoformat(last_updated),
        status=WebhookEvent.Status.PROCESSING,
    )

    try:
        # Process based on operation
        if operation in ("Create", "Update"):
            # Sync entity from QBO
            engine = SyncEngine(realm)
            engine.sync_from_qbo(
                entity_type=entity_type,
                entity_id=entity_id,
            )

            webhook_event.status = WebhookEvent.Status.PROCESSED
            webhook_event.processed_at = timezone.now()
            webhook_event.save()

            return {
                "status": "success",
                "event_id": event_id,
                "operation": operation,
            }

        elif operation == "Delete":
            # Mark entity as deleted (soft delete)
            webhook_event.status = WebhookEvent.Status.PROCESSED
            webhook_event.processed_at = timezone.now()
            webhook_event.save()

            return {
                "status": "success",
                "event_id": event_id,
                "operation": operation,
            }

        else:
            webhook_event.status = WebhookEvent.Status.FAILED
            webhook_event.error_message = f"Unsupported operation: {operation}"
            webhook_event.save()

            return {
                "status": "error",
                "error": f"Unsupported operation: {operation}",
            }

    except Exception as e:
        webhook_event.status = WebhookEvent.Status.FAILED
        webhook_event.error_message = str(e)
        webhook_event.save()

        logger.error(f"Error processing webhook event {event_id}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }


@shared_task(
    name="quickbooks_sync.cleanup_sync_logs",
    queue="quickbooks_sync",
)
def cleanup_sync_logs(days: int = 30) -> dict:
    """
    Clean up old sync logs.

    Args:
        days: Number of days to keep logs

    Returns:
        Dictionary with cleanup result
    """
    from quickbooks_sync.idempotency import idempotency_manager

    deleted_count = idempotency_manager.cleanup_expired_keys(days)

    logger.info(f"Cleaned up {deleted_count} sync logs older than {days} days")

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "days": days,
    }


@shared_task(
    name="quickbooks_sync.check_tokens",
    queue="quickbooks_sync",
)
def check_tokens() -> dict:
    """
    Check and refresh tokens that are about to expire.

    Returns:
        Dictionary with check results
    """
    # Find realms with tokens expiring within 1 hour
    expiry_threshold = timezone.now() + timezone.timedelta(hours=1)

    realms = QuickBooksRealm.objects.filter(
        is_active=True,
        token_expires_at__lt=expiry_threshold,
    )

    results = {"checked": 0, "refreshed": 0, "errors": 0}

    for realm in realms:
        results["checked"] += 1

        try:
            refresh_token.delay(realm.id)
            results["refreshed"] += 1
        except Exception as e:
            logger.error(
                f"Failed to queue token refresh for realm {realm.id}: {str(e)}"
            )
            results["errors"] += 1

    return results
