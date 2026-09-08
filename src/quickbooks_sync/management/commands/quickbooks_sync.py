"""Management command for syncing with QuickBooks."""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from quickbooks_sync.exceptions import SyncError
from quickbooks_sync.models import QuickBooksRealm
from quickbooks_sync.settings import qbs_settings
from quickbooks_sync.sync_engine import SyncEngine
from quickbooks_sync.tasks import full_sync


class Command(BaseCommand):
    help = "Sync data with QuickBooks Online"

    def add_arguments(self, parser):
        parser.add_argument(
            "--realm-id",
            type=int,
            help="QuickBooksRealm ID to sync",
        )
        parser.add_argument(
            "--all-realms",
            action="store_true",
            help="Sync all active realms",
        )
        parser.add_argument(
            "--entity-type",
            type=str,
            help="Specific entity type to sync (e.g., Customer, Invoice)",
        )
        parser.add_argument(
            "--direction",
            choices=["to_qbo", "from_qbo"],
            default="from_qbo",
            help="Sync direction (default: from_qbo)",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            help="Run sync asynchronously with Celery",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List all active realms",
        )

    def handle(self, *args, **options):
        if options["list"]:
            self.list_realms()
            return

        if options["all_realms"]:
            self.sync_all_realms(async_mode=options["async"])
            return

        if options["realm_id"]:
            self.sync_realm(
                realm_id=options["realm_id"],
                entity_type=options["entity_type"],
                direction=options["direction"],
                async_mode=options["async"],
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Please provide --realm-id, --all-realms, or --list"
                )
            )

    def list_realms(self):
        """List all active realms."""
        realms = QuickBooksRealm.objects.filter(is_active=True)

        if not realms.exists():
            self.stdout.write(self.style.WARNING("No active realms found"))
            return

        self.stdout.write(self.style.HTTP_INFO("Active QuickBooks Realms:\n"))
        self.stdout.write(f"{'ID':<6} {'Realm ID':<20} {'Company Name':<30} {'Last Sync':<20}")
        self.stdout.write("-" * 76)

        for realm in realms:
            last_sync = realm.last_sync_at.strftime("%Y-%m-%d %H:%M") if realm.last_sync_at else "Never"
            self.stdout.write(
                f"{realm.id:<6} {realm.realm_id:<20} {realm.company_name or 'N/A':<30} {last_sync:<20}"
            )

    def sync_realm(self, realm_id, entity_type=None, direction="from_qbo", async_mode=False):
        """Sync a specific realm."""
        try:
            realm = QuickBooksRealm.objects.get(id=realm_id, is_active=True)
        except QuickBooksRealm.DoesNotExist:
            raise CommandError(f"Realm {realm_id} not found or inactive")

        self.stdout.write(
            self.style.HTTP_INFO(
                f"Syncing realm: {realm.company_name} ({realm.realm_id})\n"
            )
        )

        if async_mode:
            # Queue async sync
            task = full_sync.delay(realm_id)
            self.stdout.write(
                self.style.SUCCESS(f"Sync queued with task ID: {task.id}")
            )
            return

        # Run synchronous sync
        try:
            engine = SyncEngine(realm)

            if entity_type:
                # Sync specific entity type
                if direction == "to_qbo":
                    self.stdout.write(f"  Syncing {entity_type} to QuickBooks...")
                    # This would require local entity data - simplified for now
                    self.stdout.write(
                        self.style.WARNING(
                            "  Direct to_qbo sync requires entity data. "
                            "Use the API or Celery tasks for full sync."
                        )
                    )
                else:
                    self.stdout.write(f"  Syncing {entity_type} from QuickBooks...")
                    entities = engine._sync_entity_type_from_qbo(entity_type)
                    self.stdout.write(
                        self.style.SUCCESS(f"  Synced {len(entities)} {entity_type} entities")
                    )
            else:
                # Full sync
                results = engine.full_sync()
                self.display_results(results)

        except SyncError as e:
            raise CommandError(f"Sync failed: {str(e)}")
        except Exception as e:
            raise CommandError(f"Unexpected error: {str(e)}")

    def sync_all_realms(self, async_mode=False):
        """Sync all active realms."""
        realms = QuickBooksRealm.objects.filter(is_active=True, sync_enabled=True)

        if not realms.exists():
            self.stdout.write(self.style.WARNING("No active realms with sync enabled"))
            return

        self.stdout.write(
            self.style.HTTP_INFO(f"Syncing {realms.count()} realm(s)...\n")
        )

        for realm in realms:
            self.stdout.write(f"  Syncing: {realm.company_name} ({realm.realm_id})")

            if async_mode:
                task = full_sync.delay(realm.id)
                self.stdout.write(f"    Queued with task ID: {task.id}")
            else:
                try:
                    engine = SyncEngine(realm)
                    results = engine.full_sync()
                    self.display_results(results, indent=4)
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"    Error: {str(e)}")
                    )

    def display_results(self, results, indent=2):
        """Display sync results."""
        prefix = " " * indent
        self.stdout.write(f"{prefix}Results:")
        self.stdout.write(f"{prefix}  Total synced: {results['total']}")
        self.stdout.write(f"{prefix}  Success: {results['success']}")
        self.stdout.write(f"{prefix}  Failed: {results['failed']}")

        if results["errors"]:
            self.stdout.write(f"{prefix}  Errors:")
            for entity_type, error in results["errors"].items():
                self.stdout.write(f"{prefix}    {entity_type}: {error}")

        if results["synced"]:
            self.stdout.write(f"{prefix}  Synced by type:")
            for entity_type, count in results["synced"].items():
                self.stdout.write(f"{prefix}    {entity_type}: {count}")
