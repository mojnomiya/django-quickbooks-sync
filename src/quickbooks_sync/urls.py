"""URL configuration for quickbooks_sync."""

from django.urls import path

from quickbooks_sync.webhook_handler import webhook_endpoint, webhook_test_endpoint

app_name = "quickbooks_sync"

urlpatterns = [
    path("webhook/", webhook_endpoint, name="webhook"),
    path("webhook/test/", webhook_test_endpoint, name="webhook-test"),
]
