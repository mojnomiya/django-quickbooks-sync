# django-quickbooks-sync

[![CI/CD](https://github.com/mojnomiya/django-quickbooks-sync/actions/workflows/ci.yml/badge.svg)](https://github.com/mojnomiya/django-quickbooks-sync/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/mojnomiya/django-quickbooks-sync/branch/main/graph/badge.svg)](https://codecov.io/gh/mojnomiya/django-quickbooks-sync)
[![PyPI version](https://badge.fury.io/py/django-quickbooks-sync.svg)](https://pypi.org/project/django-quickbooks-sync/)
[![Python Versions](https://img.shields.io/pypi/pyversions/django-quickbooks-sync.svg)](https://pypi.org/project/django-quickbooks-sync/)
[![Django Versions](https://img.shields.io/pypi/frameworkversions/django/django-quickbooks-sync.svg)](https://pypi.org/project/django-quickbooks-sync/)

Production-grade Django integration for QuickBooks Online with bidirectional sync, OAuth management, and audit logging.

## Features

- **OAuth 2.0 Management** - Secure token storage with automatic refresh
- **Bidirectional Sync** - Push and pull data between Django and QuickBooks
- **Celery Integration** - Async processing with retry logic
- **Rate Limiting** - Comply with QuickBooks API limits (500 req/min)
- **Idempotency** - Prevent duplicate operations
- **Audit Logging** - Complete operation history
- **Webhook Support** - Real-time event processing
- **Multi-Realm** - Support multiple QuickBooks companies

## Quick Start

### Installation

```bash
pip install django-quickbooks-sync
```

### Configuration

Add to your `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'quickbooks_sync',
]

# QuickBooks Sync Settings
QUICKBOOKS_SYNC_CLIENT_ID = 'your-client-id'
QUICKBOOKS_SYNC_CLIENT_SECRET = 'your-client-secret'
QUICKBOOKS_SYNC_REDIRECT_URI = 'http://localhost:8000/quickbooks/callback/'
QUICKBOOKS_SYNC_ENVIRONMENT = 'sandbox'  # or 'production'
QUICKBOOKS_SYNC_WEBHOOK_VERIFIER_TOKEN = 'your-webhook-token'
```

### Database Setup

```bash
python manage.py migrate
```

### URL Configuration

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path('quickbooks/', include('quickbooks_sync.urls')),
]
```

## Usage

### Management Commands

```bash
# Setup QuickBooks connection
python manage.py quickbooks_setup --interactive

# Validate configuration
python manage.py quickbooks_setup --validate

# List connected realms
python manage.py quickbooks_sync --list

# Sync data
python manage.py quickbooks_sync --realm-id 1
python manage.py quickbooks_sync --all-realms
python manage.py quickbooks_sync --all-realms --async

# Webhook management
python manage.py quickbooks_webhook --setup
python manage.py quickbooks_webhook --list-events
```

### Python API

```python
from quickbooks_sync.models import QuickBooksRealm
from quickbooks_sync.sync_engine import SyncEngine
from quickbooks_sync.tasks import full_sync

# Get a realm
realm = QuickBooksRealm.objects.get(realm_id='123456789')

# Synchronous sync
engine = SyncEngine(realm)
results = engine.full_sync()

# Async sync with Celery
task = full_sync.delay(realm.id)

# Sync specific entity
entity_data = engine.sync_from_qbo('Customer', '123')

# Sync to QuickBooks
sync_log = engine.sync_to_qbo(
    entity_type='Customer',
    entity_id='local_123',
    entity_data={'name': 'John Doe'}
)
```

### Celery Configuration

```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    'check-tokens-every-hour': {
        'task': 'quickbooks_sync.tasks.check_tokens',
        'schedule': 3600.0,
    },
    'cleanup-sync-logs-daily': {
        'task': 'quickbooks_sync.tasks.cleanup_sync_logs',
        'schedule': 86400.0,
    },
}
```

## Supported Entities

| Entity | Sync | Notes |
|--------|------|-------|
| Account | ✓ | Chart of Accounts |
| Customer | ✓ | Customer records |
| Vendor | ✓ | Vendor records |
| Employee | ✓ | Employee records |
| Invoice | ✓ | Sales invoices |
| Bill | ✓ | Purchase bills |
| Payment | ✓ | Payment records |
| Item | ✓ | Inventory/Service items |

## Webhook Setup

1. Register your webhook in the [Intuit Developer Portal](https://developer.intuit.com)
2. Set your webhook URL: `https://your-domain.com/quickbooks/webhook/`
3. Configure the verifier token in settings
4. Run: `python manage.py quickbooks_webhook --setup` for detailed instructions

## Rate Limiting

QuickBooks API limits:
- 500 requests per minute per realm
- 10 concurrent requests per second per realm

The package automatically handles rate limiting with exponential backoff.

## Conflict Resolution

Three strategies available:

1. **last_write_wins** (default) - Most recent update wins
2. **source_wins** - Local Django data always wins
3. **manual** - Requires manual conflict resolution

Configure in settings:
```python
QUICKBOOKS_SYNC_CONFLICT_RESOLUTION = 'last_write_wins'
```

## Development

### Setup

```bash
git clone https://github.com/mojnomiya/django-quickbooks-sync.git
cd django-quickbooks-sync
python -m venv venv
source venv/bin/activate
pip install -e ".[dev,test]"
```

### Running Tests

```bash
pytest tests/ --cov=quickbooks_sync --cov-report=term-missing
```

### Code Quality

```bash
# Linting
ruff check src/ tests/

# Formatting
black src/ tests/

# Type checking
mypy src/quickbooks_sync/
```

## Documentation

- [Software Requirements Specification](docs/srs.md)
- [Architecture Document](docs/architecture.md)
- [API Reference](docs/api_reference.md) (coming soon)
- [User Guide](docs/user_guide.md) (coming soon)
- [Contributing Guide](docs/contributing.md) (coming soon)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- [GitHub Issues](https://github.com/mojnomiya/django-quickbooks-sync/issues)
- [Documentation](https://django-quickbooks-sync.readthedocs.io/)

## Acknowledgments

- [python-quickbooks](https://github.com/ej2/python-quickbooks) - Base QuickBooks API library
- [Django](https://www.djangoproject.com/) - The web framework
- [Celery](https://docs.celeryq.dev/) - Distributed task queue
