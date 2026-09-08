"""Test configuration for quickbooks_sync."""

import os
import sys

import django
from django.conf import settings


def pytest_configure(config):
    """Configure pytest with Django settings."""
    # Add the project root to Python path
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.django_settings")

    # Configure Django settings
    if not settings.configured:
        settings.configure(
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "quickbooks_sync",
            ],
            QUICKBOOKS_SYNC_CLIENT_ID="test_client_id",
            QUICKBOOKS_SYNC_CLIENT_SECRET="test_client_secret",
            QUICKBOOKS_SYNC_REDIRECT_URI="http://localhost:8000/callback",
            QUICKBOOKS_SYNC_ENVIRONMENT="sandbox",
            QUICKBOOKS_SYNC_WEBHOOK_VERIFIER_TOKEN="test_verifier_token",
            USE_TZ=True,
        )

    django.setup()
