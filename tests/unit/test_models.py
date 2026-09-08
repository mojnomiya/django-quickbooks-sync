"""Tests for quickbooks_sync models."""

import pytest
from django.test import TestCase
from django.utils import timezone

from quickbooks_sync.models import AuditEntry, QuickBooksRealm, SyncLog, WebhookEvent


class QuickBooksRealmTest(TestCase):
    """Tests for QuickBooksRealm model."""

    def test_create_realm(self):
        """Test creating a QuickBooks realm."""
        realm = QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertEqual(realm.realm_id, "123456789")
        self.assertEqual(realm.company_name, "Test Company")
        self.assertTrue(realm.is_active)
        self.assertTrue(realm.sync_enabled)

    def test_str_representation(self):
        """Test string representation of realm."""
        realm = QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertEqual(str(realm), "Test Company (123456789)")

    def test_is_token_expired(self):
        """Test token expiry check."""
        realm = QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=timezone.now() - timezone.timedelta(minutes=10),
        )
        self.assertTrue(realm.is_token_expired)

    def test_is_token_not_expired(self):
        """Test token not expired."""
        realm = QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertFalse(realm.is_token_expired)

    def test_unique_realm_id(self):
        """Test realm_id uniqueness."""
        QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        with self.assertRaises(Exception):
            QuickBooksRealm.objects.create(
                realm_id="123456789",
                company_name="Another Company",
                access_token="test_access_token",
                refresh_token="test_refresh_token",
                token_expires_at=timezone.now() + timezone.timedelta(hours=1),
            )


class SyncLogTest(TestCase):
    """Tests for SyncLog model."""

    def setUp(self):
        self.realm = QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    def test_create_sync_log(self):
        """Test creating a sync log."""
        sync_log = SyncLog.objects.create(
            realm=self.realm,
            entity_type="Customer",
            entity_id="123",
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key="test_key_123",
            payload={"name": "Test Customer"},
        )
        self.assertEqual(sync_log.entity_type, "Customer")
        self.assertEqual(sync_log.status, SyncLog.Status.PENDING)

    def test_str_representation(self):
        """Test string representation."""
        sync_log = SyncLog.objects.create(
            realm=self.realm,
            entity_type="Customer",
            entity_id="123",
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key="test_key_123",
        )
        self.assertIn("Customer", str(sync_log))
        self.assertIn("To QuickBooks", str(sync_log))

    def test_unique_idempotency_key(self):
        """Test idempotency_key uniqueness."""
        SyncLog.objects.create(
            realm=self.realm,
            entity_type="Customer",
            entity_id="123",
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key="test_key_123",
        )
        with self.assertRaises(Exception):
            SyncLog.objects.create(
                realm=self.realm,
                entity_type="Customer",
                entity_id="456",
                direction=SyncLog.Direction.TO_QBO,
                idempotency_key="test_key_123",
            )


class AuditEntryTest(TestCase):
    """Tests for AuditEntry model."""

    def setUp(self):
        self.realm = QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    def test_create_audit_entry(self):
        """Test creating an audit entry."""
        audit_entry = AuditEntry.objects.create(
            realm=self.realm,
            entity_type="Customer",
            entity_id="123",
            action=AuditEntry.Action.CREATE,
            payload={"name": "Test Customer"},
            outcome="success",
        )
        self.assertEqual(audit_entry.action, AuditEntry.Action.CREATE)
        self.assertEqual(audit_entry.outcome, "success")

    def test_str_representation(self):
        """Test string representation."""
        audit_entry = AuditEntry.objects.create(
            realm=self.realm,
            entity_type="Customer",
            entity_id="123",
            action=AuditEntry.Action.CREATE,
            payload={"name": "Test Customer"},
            outcome="success",
        )
        self.assertIn("Create", str(audit_entry))
        self.assertIn("success", str(audit_entry))


class WebhookEventTest(TestCase):
    """Tests for WebhookEvent model."""

    def setUp(self):
        self.realm = QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    def test_create_webhook_event(self):
        """Test creating a webhook event."""
        webhook_event = WebhookEvent.objects.create(
            realm=self.realm,
            event_id="test_event_123",
            entity_type="Invoice",
            entity_id="456",
            operation="Create",
            last_updated=timezone.now(),
            payload={"test": "data"},
        )
        self.assertEqual(webhook_event.operation, "Create")
        self.assertEqual(webhook_event.status, WebhookEvent.Status.RECEIVED)

    def test_str_representation(self):
        """Test string representation."""
        webhook_event = WebhookEvent.objects.create(
            realm=self.realm,
            event_id="test_event_123",
            entity_type="Invoice",
            entity_id="456",
            operation="Create",
            last_updated=timezone.now(),
            payload={"test": "data"},
        )
        self.assertIn("Create", str(webhook_event))
        self.assertIn("Invoice", str(webhook_event))
