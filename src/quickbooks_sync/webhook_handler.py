"""Webhook handler for QuickBooks events."""

import hashlib
import hmac
import json
import logging
from typing import Optional

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from quickbooks_sync.exceptions import WebhookError
from quickbooks_sync.models import QuickBooksRealm, WebhookEvent
from quickbooks_sync.settings import qbs_settings
from quickbooks_sync.tasks import process_webhook

logger = logging.getLogger(__name__)


def verify_webhook_signature(payload: str, signature: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.

    Args:
        payload: Raw request body
        signature: Signature from request header

    Returns:
        True if signature is valid
    """
    verifier_token = qbs_settings.WEBHOOK_VERIFIER_TOKEN
    if not verifier_token:
        logger.warning("Webhook verifier token not configured")
        return False

    expected = hmac.new(
        verifier_token.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def parse_webhook_payload(payload: dict) -> list[dict]:
    """
    Parse webhook payload from QuickBooks.

    Args:
        payload: Raw webhook payload

    Returns:
        List of parsed events
    """
    events = []

    # QuickBooks webhook format
    event_notifications = payload.get("eventNotifications", [])

    for notification in event_notifications:
        realm_id = notification.get("realmId")
        data_change_event = notification.get("dataChangeEvent", {})
        entities = data_change_event.get("entities", [])

        for entity in entities:
            events.append(
                {
                    "realm_id": realm_id,
                    "entity_type": entity.get("name"),
                    "entity_id": entity.get("id"),
                    "operation": entity.get("operation"),
                    "last_updated": entity.get("lastUpdated"),
                }
            )

    return events


@csrf_exempt
@require_POST
def webhook_endpoint(request: HttpRequest) -> HttpResponse:
    """
    Webhook endpoint for QuickBooks events.

    This endpoint receives webhook notifications from QuickBooks
    and queues them for processing.
    """
    # Check if webhooks are enabled
    if not qbs_settings.WEBHOOK_ENABLED:
        return JsonResponse(
            {"error": "Webhooks are not enabled"},
            status=400,
        )

    # Get signature from header
    signature = request.headers.get("intuit-signature")
    if not signature:
        return JsonResponse(
            {"error": "Missing signature header"},
            status=400,
        )

    # Get raw body
    try:
        body = request.body.decode("utf-8")
    except UnicodeDecodeError:
        return JsonResponse(
            {"error": "Invalid request body"},
            status=400,
        )

    # Verify signature
    if not verify_webhook_signature(body, signature):
        logger.warning("Invalid webhook signature")
        return JsonResponse(
            {"error": "Invalid signature"},
            status=401,
        )

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400,
        )

    # Parse events
    try:
        events = parse_webhook_payload(payload)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {str(e)}")
        return JsonResponse(
            {"error": "Failed to parse payload"},
            status=400,
        )

    # Process each event
    processed_count = 0
    for event in events:
        try:
            # Find the realm
            realm = QuickBooksRealm.objects.get(
                realm_id=event["realm_id"],
                is_active=True,
            )

            # Generate unique event ID
            event_id = f"{event['realm_id']}:{event['entity_type']}:{event['entity_id']}:{event['operation']}:{event['last_updated']}"

            # Queue for async processing
            process_webhook.delay(
                realm_id=realm.id,
                event_id=event_id,
                entity_type=event["entity_type"],
                entity_id=event["entity_id"],
                operation=event["operation"],
                last_updated=event["last_updated"],
            )

            processed_count += 1

        except QuickBooksRealm.DoesNotExist:
            logger.warning(f"Realm {event['realm_id']} not found or inactive")
            continue
        except Exception as e:
            logger.error(f"Failed to queue webhook event: {str(e)}")
            continue

    return JsonResponse(
        {
            "status": "success",
            "events_received": len(events),
            "events_queued": processed_count,
        }
    )


@csrf_exempt
def webhook_test_endpoint(request: HttpRequest) -> HttpResponse:
    """
    Test endpoint for webhook verification.

    QuickBooks sends a verification request to check if the endpoint is valid.
    """
    if request.method == "GET":
        # Return a simple response to verify endpoint is working
        return JsonResponse(
            {
                "status": "ok",
                "message": "QuickBooks webhook endpoint is working",
            }
        )

    return JsonResponse(
        {"error": "Method not allowed"},
        status=405,
    )
