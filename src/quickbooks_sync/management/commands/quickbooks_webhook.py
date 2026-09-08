"""Management command for webhook setup."""

from django.core.management.base import BaseCommand, CommandError

from quickbooks_sync.models import QuickBooksRealm, WebhookEvent
from quickbooks_sync.settings import qbs_settings


class Command(BaseCommand):
    help = "Manage QuickBooks webhook configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--setup",
            action="store_true",
            help="Show webhook setup instructions",
        )
        parser.add_argument(
            "--list-events",
            action="store_true",
            help="List recent webhook events",
        )
        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Retry failed webhook events",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of events to list (default: 10)",
        )

    def handle(self, *args, **options):
        if options["setup"]:
            self.show_setup_instructions()
            return

        if options["list_events"]:
            self.list_events(options["count"])
            return

        if options["retry_failed"]:
            self.retry_failed_events()
            return

        self.stdout.write(
            self.style.WARNING("Please specify an action: --setup, --list-events, or --retry-failed")
        )

    def show_setup_instructions(self):
        """Show webhook setup instructions."""
        self.stdout.write(self.style.HTTP_INFO("QuickBooks Webhook Setup Instructions\n"))
        self.stdout.write("=" * 60)

        self.stdout.write("\n1. Register your webhook endpoint in the Intuit Developer Portal:")
        self.stdout.write("   - Go to https://developer.intuit.com/app/developer/dashboard")
        self.stdout.write("   - Select your app")
        self.stdout.write("   - Go to 'Keys & OAuth' > 'Your App's Webhooks'")
        self.stdout.write(f"   - Enter your webhook URL: https://your-domain.com/quickbooks/webhook/")
        self.stdout.write(f"   - Enter the Verifier Token: {qbs_settings.WEBHOOK_VERIFIER_TOKEN or 'NOT SET'}")

        self.stdout.write("\n2. Configure your Django settings:")
        self.stdout.write("   Add to your settings.py:")
        self.stdout.write("   ```")
        self.stdout.write("   QUICKBOOKS_SYNC_WEBHOOK_ENABLED = True")
        self.stdout.write(f"   QUICKBOOKS_SYNC_WEBHOOK_VERIFIER_TOKEN = '{qbs_settings.WEBHOOK_VERIFIER_TOKEN or 'your-verifier-token'}'")
        self.stdout.write("   ```")

        self.stdout.write("\n3. Add URL configuration:")
        self.stdout.write("   Add to your urls.py:")
        self.stdout.write("   ```")
        self.stdout.write("   from django.urls import path, include")
        self.stdout.write("   urlpatterns = [")
        self.stdout.write("       path('quickbooks/', include('quickbooks_sync.urls'))")
        self.stdout.write("   ]")
        self.stdout.write("   ```")

        self.stdout.write("\n4. Test your webhook endpoint:")
        self.stdout.write("   Use the Intuit webhook testing tool in the developer portal")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                "Note: Webhooks require HTTPS in production. "
                "Use a service like ngrok for local development."
            )
        )

    def list_events(self, count):
        """List recent webhook events."""
        events = WebhookEvent.objects.all()[:count]

        if not events.exists():
            self.stdout.write(self.style.WARNING("No webhook events found"))
            return

        self.stdout.write(self.style.HTTP_INFO(f"Recent Webhook Events ({count}):\n"))
        self.stdout.write(
            f"{'ID':<6} {'Event ID':<20} {'Entity':<15} {'Operation':<10} {'Status':<12} {'Created':<20}"
        )
        self.stdout.write("-" * 83)

        for event in events:
            created = event.created_at.strftime("%Y-%m-%d %H:%M:%S")
            self.stdout.write(
                f"{event.id:<6} {event.event_id:<20} {event.entity_type:<15} "
                f"{event.operation:<10} {event.get_status_display():<12} {created:<20}"
            )

    def retry_failed_events(self):
        """Retry failed webhook events."""
        failed_events = WebhookEvent.objects.filter(status=WebhookEvent.Status.FAILED)

        if not failed_events.exists():
            self.stdout.write(self.style.WARNING("No failed webhook events found"))
            return

        self.stdout.write(
            self.style.HTTP_INFO(f"Retrying {failed_events.count()} failed event(s)...\n")
        )

        from quickbooks_sync.tasks import process_webhook

        for event in failed_events:
            self.stdout.write(f"  Retrying event: {event.event_id}")
            try:
                process_webhook.delay(
                    realm_id=event.realm.id,
                    event_id=event.event_id,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                    operation=event.operation,
                    last_updated=event.last_updated.isoformat(),
                )
                self.stdout.write(self.style.SUCCESS(f"    Queued for retry"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"    Failed to queue: {str(e)}"))
