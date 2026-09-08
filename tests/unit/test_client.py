"""Tests for quickbooks_sync client."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from quickbooks_sync.client import QuickBooksClient
from quickbooks_sync.exceptions import APIError, OAuthError, RateLimitError


class QuickBooksClientTest(TestCase):
    """Tests for QuickBooksClient."""

    def setUp(self):
        self.client = QuickBooksClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            realm_id="123456789",
            environment="sandbox",
        )

    def test_client_initialization(self):
        """Test client initialization."""
        self.assertEqual(self.client.client_id, "test_client_id")
        self.assertEqual(self.client.client_secret, "test_client_secret")
        self.assertEqual(self.client.realm_id, "123456789")
        self.assertEqual(self.client.environment, "sandbox")

    def test_to_dict(self):
        """Test client to_dict method."""
        result = self.client.to_dict()
        self.assertIn("realm_id", result)
        self.assertIn("environment", result)
        self.assertIn("client_id", result)

    @patch("quickbooks_sync.client.AuthClient")
    def test_get_authorization_url(self, mock_auth_client):
        """Test getting authorization URL."""
        mock_auth_client.return_value.get_authorization_url.return_value = (
            "https://appcenter.intuit.com/connect/oauth2"
        )
        url = self.client.get_authorization_url()
        self.assertIn("https", url)

    @patch("quickbooks_sync.client.AuthClient")
    def test_exchange_code_success(self, mock_auth_client):
        """Test successful code exchange."""
        mock_auth_client.return_value.create_token.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "bearer",
            "expires_in": 3600,
        }
        result = self.client.exchange_code(
            "https://example.com/callback?code=abc123&realmId=123456789"
        )
        self.assertEqual(result["access_token"], "new_access_token")
        self.assertEqual(result["refresh_token"], "new_refresh_token")

    @patch("quickbooks_sync.client.AuthClient")
    def test_exchange_code_failure(self, mock_auth_client):
        """Test failed code exchange."""
        mock_auth_client.return_value.create_token.side_effect = Exception("Invalid code")
        with self.assertRaises(OAuthError):
            self.client.exchange_code(
                "https://example.com/callback?code=invalid"
            )

    @patch("quickbooks_sync.client.AuthClient")
    def test_refresh_access_token_success(self, mock_auth_client):
        """Test successful token refresh."""
        mock_auth_client.return_value.refresh.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "expires_in": 3600,
        }
        result = self.client.refresh_access_token()
        self.assertEqual(result["access_token"], "refreshed_access_token")

    @patch("quickbooks_sync.client.AuthClient")
    def test_refresh_access_token_failure(self, mock_auth_client):
        """Test failed token refresh."""
        mock_auth_client.return_value.refresh.side_effect = Exception("Token expired")
        with self.assertRaises(OAuthError):
            self.client.refresh_access_token()

    @patch("quickbooks_sync.client.QuickBooks")
    def test_get_entity_success(self, mock_qb):
        """Test successful entity retrieval."""
        mock_entity = MagicMock()
        mock_entity.id = "123"
        mock_qb.return_value.get_entity.return_value = mock_entity
        result = self.client.get_entity("Customer", "123")
        self.assertIsNotNone(result)

    @patch("quickbooks_sync.client.QuickBooks")
    def test_get_entity_unknown_type(self, mock_qb):
        """Test unknown entity type."""
        with self.assertRaises(APIError):
            self.client.get_entity("UnknownEntity", "123")

    @patch("quickbooks_sync.client.QuickBooks")
    def test_create_entity_success(self, mock_qb):
        """Test successful entity creation."""
        mock_entity = MagicMock()
        mock_entity.id = "456"
        mock_entity.save.return_value = None
        mock_qb.return_value.create_entity.return_value = mock_entity
        result = self.client.create_entity("Customer", {"name": "Test"})
        self.assertIsNotNone(result)

    @patch("quickbooks_sync.client.QuickBooks")
    def test_update_entity_success(self, mock_qb):
        """Test successful entity update."""
        mock_entity = MagicMock()
        mock_entity.id = "123"
        mock_entity.save.return_value = None
        mock_qb.return_value.update_entity.return_value = mock_entity
        result = self.client.update_entity("Customer", "123", {"name": "Updated"})
        self.assertIsNotNone(result)

    @patch("quickbooks_sync.client.QuickBooks")
    def test_delete_entity_success(self, mock_qb):
        """Test successful entity deletion."""
        mock_entity = MagicMock()
        mock_entity.delete.return_value = None
        mock_qb.return_value.delete_entity.return_value = mock_entity
        result = self.client.delete_entity("Customer", "123")
        self.assertTrue(result)
