"""Management command for setting up QuickBooks sync."""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from quickbooks_sync.client import QuickBooksClient
from quickbooks_sync.exceptions import OAuthError
from quickbooks_sync.models import QuickBooksRealm
from quickbooks_sync.settings import qbs_settings, validate_settings


class Command(BaseCommand):
    help = "Set up QuickBooks Online integration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--realm-id",
            type=str,
            help="QuickBooks realm ID (company ID)",
        )
        parser.add_argument(
            "--access-token",
            type=str,
            help="OAuth access token",
        )
        parser.add_argument(
            "--refresh-token",
            type=str,
            help="OAuth refresh token",
        )
        parser.add_argument(
            "--company-name",
            type=str,
            help="Company name",
        )
        parser.add_argument(
            "--interactive",
            action="store_true",
            help="Interactive setup mode",
        )
        parser.add_argument(
            "--validate",
            action="store_true",
            help="Validate current configuration",
        )

    def handle(self, *args, **options):
        if options["validate"]:
            self.validate_config()
            return

        if options["interactive"]:
            self.interactive_setup()
            return

        if options["realm_id"]:
            self.setup_with_tokens(
                realm_id=options["realm_id"],
                access_token=options["access_token"],
                refresh_token=options["refresh_token"],
                company_name=options["company_name"],
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Please provide --realm-id or use --interactive mode"
                )
            )

    def validate_config(self):
        """Validate current configuration."""
        self.stdout.write("Validating QuickBooks Sync configuration...\n")

        errors = validate_settings()
        if errors:
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            raise CommandError("Configuration validation failed")
        else:
            self.stdout.write(self.style.SUCCESS("Configuration is valid!"))

        # Check for existing realms
        realm_count = QuickBooksRealm.objects.filter(is_active=True).count()
        self.stdout.write(f"  Active realms: {realm_count}")

        if realm_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    "  No active realms found. Run setup with --interactive"
                )
            )

    def interactive_setup(self):
        """Interactive setup mode."""
        self.stdout.write(self.style.HTTP_INFO("QuickBooks Sync Interactive Setup\n"))

        # Validate settings first
        errors = validate_settings()
        if errors:
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            raise CommandError(
                "Please fix configuration errors before running setup"
            )

        # Get realm details
        realm_id = input("QuickBooks Realm ID (Company ID): ").strip()
        if not realm_id:
            raise CommandError("Realm ID is required")

        company_name = input("Company Name (optional): ").strip()

        access_token = input("Access Token: ").strip()
        if not access_token:
            raise CommandError("Access Token is required")

        refresh_token = input("Refresh Token: ").strip()
        if not refresh_token:
            raise CommandError("Refresh Token is required")

        # Create or update realm
        realm, created = QuickBooksRealm.objects.update_or_create(
            realm_id=realm_id,
            defaults={
                "company_name": company_name,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires_at": timezone.now() + timezone.timedelta(hours=1),
                "is_active": True,
                "sync_enabled": True,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created new realm: {realm.company_name} ({realm.realm_id})")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Updated existing realm: {realm.company_name} ({realm.realm_id})")
            )

        # Test connection
        self.stdout.write("\nTesting connection to QuickBooks...")
        try:
            client = QuickBooksClient(
                access_token=access_token,
                refresh_token=refresh_token,
                realm_id=realm_id,
            )
            company_info = client.get_company_info()
            self.stdout.write(self.style.SUCCESS(f"  Connected to: {company_info.CompanyName}"))
        except OAuthError as e:
            self.stdout.write(self.style.WARNING(f"  Warning: Could not verify connection: {e}"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Warning: Could not verify connection: {e}"))

        self.stdout.write(
            self.style.SUCCESS("\nSetup complete! You can now use QuickBooks Sync.")
        )

    def setup_with_tokens(self, realm_id, access_token, refresh_token, company_name=None):
        """Setup with provided tokens."""
        if not access_token or not refresh_token:
            raise CommandError("Both --access-token and --refresh-token are required")

        # Create or update realm
        realm, created = QuickBooksRealm.objects.update_or_create(
            realm_id=realm_id,
            defaults={
                "company_name": company_name or f"Company {realm_id}",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires_at": timezone.now() + timezone.timedelta(hours=1),
                "is_active": True,
                "sync_enabled": True,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created new realm: {realm.company_name} ({realm.realm_id})")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Updated existing realm: {realm.company_name} ({realm.realm_id})")
            )

        # Test connection
        self.stdout.write("\nTesting connection to QuickBooks...")
        try:
            client = QuickBooksClient(
                access_token=access_token,
                refresh_token=refresh_token,
                realm_id=realm_id,
            )
            company_info = client.get_company_info()
            self.stdout.write(self.style.SUCCESS(f"  Connected to: {company_info.CompanyName}"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Warning: Could not verify connection: {e}"))

        self.stdout.write(
            self.style.SUCCESS("\nSetup complete!")
        )
