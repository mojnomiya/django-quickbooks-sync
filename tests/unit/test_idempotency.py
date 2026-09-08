"""Tests for quickbooks_sync idempotency."""

from django.test import TestCase

from quickbooks_sync.exceptions import IdempotencyError
from quickbooks_sync.idempotency import IdempotencyManager
from quickbooks_sync.models import QuickBooksRealm, SyncLog


class IdempotencyManagerTest(TestCase):
    """Tests for IdempotencyManager."""

    def setUp(self):
        self.manager = IdempotencyManager(enabled=True)
        self.realm = QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at="2025-12-31T23:59:59Z",
        )

    def test_generate_key(self):
        """Test idempotency key generation."""
        key = self.manager.generate_key("Customer", "123", "create")
        self.assertIsInstance(key, str)
        self.assertEqual(len(key), 64)  # SHA256 hex digest

    def test_generate_deterministic_key(self):
        """Test key generation is deterministic."""
        key1 = self.manager.generate_key("Customer", "123", "create")
        key2 = self.manager.generate_key("Customer", "123", "create")
        self.assertEqual(key1, key2)

    def test_check_key_not_found(self):
        """Test checking non-existent key."""
        result = self.manager.check_key("nonexistent_key")
        self.assertIsNone(result)

    def test_create_log(self):
        """Test creating sync log."""
        sync_log = self.manager.create_log(
            realm_id=self.realm.id,
            entity_type="Customer",
            entity_id="123",
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key="test_key_123",
        )
        self.assertEqual(sync_log.entity_type, "Customer")
        self.assertEqual(sync_log.status, SyncLog.Status.PENDING)

    def test_create_log_duplicate_key(self):
        """Test creating sync log with duplicate key."""
        self.manager.create_log(
            realm_id=self.realm.id,
            entity_type="Customer",
            entity_id="123",
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key="test_key_123",
        )
        with self.assertRaises(IdempotencyError):
            self.manager.create_log(
                realm_id=self.realm.id,
                entity_type="Customer",
                entity_id="123",
                direction=SyncLog.Direction.TO_QBO,
                idempotency_key="test_key_123",
            )

    def test_update_log(self):
        """Test updating sync log."""
        sync_log = self.manager.create_log(
            realm_id=self.realm.id,
            entity_type="Customer",
            entity_id="123",
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key="test_key_123",
        )
        updated_log = self.manager.update_log(
            sync_log,
            status=SyncLog.Status.SUCCESS,
            response={"id": "456"},
        )
        self.assertEqual(updated_log.status, SyncLog.Status.SUCCESS)
        self.assertEqual(updated_log.response, {"id": "456"})

    def test_check_key_found(self):
        """Test checking existing key."""
        sync_log = self.manager.create_log(
            realm_id=self.realm.id,
            entity_type="Customer",
            entity_id="123",
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key="test_key_123",
        )
        result = self.manager.check_key("test_key_123")
        self.assertIsNotNone(result)
        self.assertEqual(result.id, sync_log.id)

    def test_cleanup_expired_keys(self):
        """Test cleaning up expired keys."""
        sync_log = self.manager.create_log(
            realm_id=self.realm.id,
            entity_type="Customer",
            entity_id="123",
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key="test_key_123",
        )
        # Make the log old
        SyncLog.objects.filter(id=sync_log.id).update(
            created_at="2020-01-01T00:00:00Z"
        )
        deleted_count = self.manager.cleanup_expired_keys(days=30)
        self.assertGreater(deleted_count, 0)

    def test_disabled_manager(self):
        """Test disabled idempotency manager."""
        manager = IdempotencyManager(enabled=False)
        result = manager.check_key("any_key")
        self.assertIsNone(result)

        sync_log = manager.create_log(
            realm_id=self.realm.id,
            entity_type="Customer",
            entity_id="123",
            direction=SyncLog.Direction.TO_QBO,
            idempotency_key="test_key_123",
        )
        self.assertIsNotNone(sync_log)
