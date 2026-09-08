"""Tests for quickbooks_sync sync engine."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from quickbooks_sync.exceptions import SyncError
from quickbooks_sync.models import AuditEntry, QuickBooksRealm, SyncLog
from quickbooks_sync.sync_engine import SyncEngine


class SyncEngineTest(TestCase):
    """Tests for SyncEngine."""

    def setUp(self):
        self.realm = QuickBooksRealm.objects.create(
            realm_id="123456789",
            company_name="Test Company",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        self.engine = SyncEngine(self.realm)

    @patch("quickbooks_sync.sync_engine.QuickBooksClient")
    def test_sync_to_qbo(self, mock_client_class):
        """Test syncing to QuickBooks."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock entity doesn't exist, so create it
        mock_client.get_entity.side_effect = Exception("Not found")
        mock_entity = MagicMock()
        mock_entity.id = "456"
        mock_client.create_entity.return_value = mock_entity

        result = self.engine.sync_to_qbo(
            entity_type="Customer",
            entity_id="local_123",
            entity_data={"name": "Test Customer"},
        )

        self.assertEqual(result.status, SyncLog.Status.SUCCESS)

    @patch("quickbooks_sync.sync_engine.QuickBooksClient")
    def test_sync_from_qbo(self, mock_client_class):
        """Test syncing from QuickBooks."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_entity = MagicMock()
        mock_entity.id = "123"
        mock_entity.to_dict.return_value = {
            "id": "123",
            "name": "Test Customer",
        }
        mock_client.get_entity.return_value = mock_entity

        result = self.engine.sync_from_qbo(
            entity_type="Customer",
            entity_id="123",
        )

        self.assertIn("id", result)
        self.assertEqual(result["id"], "123")

    @patch("quickbooks_sync.sync_engine.QuickBooksClient")
    def test_sync_to_qbo_error(self, mock_client_class):
        """Test sync to QuickBooks with error."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.get_entity.side_effect = Exception("Not found")
        mock_client.create_entity.side_effect = Exception("API Error")

        with self.assertRaises(SyncError):
            self.engine.sync_to_qbo(
                entity_type="Customer",
                entity_id="local_123",
                entity_data={"name": "Test Customer"},
            )

    @patch("quickbooks_sync.sync_engine.QuickBooksClient")
    def test_full_sync(self, mock_client_class):
        """Test full sync."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock empty results
        mock_client.query_entities.return_value = []

        results = self.engine.full_sync(entity_types=["Customer"])

        self.assertIn("synced", results)
        self.assertIn("errors", results)

    def test_entity_to_dict(self):
        """Test entity to dict conversion."""
        mock_entity = MagicMock()
        mock_entity.to_dict.return_value = {"id": "123", "name": "Test"}
        result = self.engine._entity_to_dict(mock_entity)
        self.assertEqual(result["id"], "123")

    def test_entity_to_dict_no_to_dict(self):
        """Test entity to dict without to_dict method."""
        mock_entity = MagicMock(spec=[])  # No spec methods
        mock_entity.id = "123"
        mock_entity.name = "Test"
        result = self.engine._entity_to_dict(mock_entity)
        self.assertIn("id", result)
