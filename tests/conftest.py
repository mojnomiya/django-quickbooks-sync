"""Test configuration for quickbooks_sync."""

import pytest
from django.conf import settings


def pytest_configure(config):
    """Configure pytest with Django settings."""
    settings.DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
    settings.INSTALLED_APPS = [
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "quickbooks_sync",
    ]
    settings.QUICKBOOKS_SYNC_CLIENT_ID = "test_client_id"
    settings.QUICKBOOKS_SYNC_CLIENT_SECRET = "test_client_secret"
    settings.QUICKBOOKS_SYNC_REDIRECT_URI = "http://localhost:8000/callback"
    settings.QUICKBOOKS_SYNC_ENVIRONMENT = "sandbox"
    settings.QUICKBOOKS_SYNC_WEBHOOK_VERIFIER_TOKEN = "test_verifier_token"
