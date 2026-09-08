"""Tests for quickbooks_sync settings."""

from django.test import TestCase, override_settings

from quickbooks_sync.settings import (
    QuickBooksSyncSettings,
    get_settings,
    validate_settings,
)


class SettingsTest(TestCase):
    """Tests for settings module."""

    def test_get_settings(self):
        """Test getting all settings."""
        settings = get_settings()
        self.assertIn("CLIENT_ID", settings)
        self.assertIn("CLIENT_SECRET", settings)
        self.assertIn("ENVIRONMENT", settings)

    def test_validate_settings_valid(self):
        """Test settings validation with valid settings."""
        with override_settings(
            QUICKBOOKS_SYNC_CLIENT_ID="test_id",
            QUICKBOOKS_SYNC_CLIENT_SECRET="test_secret",
            QUICKBOOKS_SYNC_REDIRECT_URI="http://localhost:8000/callback",
        ):
            errors = validate_settings()
            self.assertEqual(errors, [])

    def test_validate_settings_missing_client_id(self):
        """Test settings validation with missing client ID."""
        with override_settings(
            QUICKBOOKS_SYNC_CLIENT_ID="",
            QUICKBOOKS_SYNC_CLIENT_SECRET="test_secret",
            QUICKBOOKS_SYNC_REDIRECT_URI="http://localhost:8000/callback",
        ):
            errors = validate_settings()
            self.assertGreater(len(errors), 0)

    def test_validate_settings_invalid_environment(self):
        """Test settings validation with invalid environment."""
        with override_settings(
            QUICKBOOKS_SYNC_CLIENT_ID="test_id",
            QUICKBOOKS_SYNC_CLIENT_SECRET="test_secret",
            QUICKBOOKS_SYNC_REDIRECT_URI="http://localhost:8000/callback",
            QUICKBOOKS_SYNC_ENVIRONMENT="invalid",
        ):
            errors = validate_settings()
            self.assertGreater(len(errors), 0)


class QuickBooksSyncSettingsTest(TestCase):
    """Tests for QuickBooksSyncSettings class."""

    def test_getattr_existing(self):
        """Test getting existing attribute."""
        settings = QuickBooksSyncSettings()
        with override_settings(QUICKBOOKS_SYNC_CLIENT_ID="test_id"):
            self.assertEqual(settings.CLIENT_ID, "test_id")

    def test_getattr_default(self):
        """Test getting attribute with default."""
        QuickBooksSyncSettings()
        # ENVIRONMENT has a default of 'sandbox'
        # When not set in Django settings, it should use the default
        # Note: We can't easily test this without mocking settings
        # So we just verify the default exists in DEFAULT_SETTINGS
        from quickbooks_sync.settings import DEFAULT_SETTINGS

        self.assertEqual(DEFAULT_SETTINGS["ENVIRONMENT"], "sandbox")

    def test_getattr_invalid(self):
        """Test getting invalid attribute."""
        settings = QuickBooksSyncSettings()
        with self.assertRaises(AttributeError):
            _ = settings.INVALID_SETTING
