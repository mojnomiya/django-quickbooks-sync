# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- OAuth 2.0 management with automatic token refresh
- Bidirectional sync engine
- Rate limiting (500 req/min, 10 concurrent/sec)
- Idempotency key generation and verification
- Audit logging for all operations
- Webhook handling with signature verification
- Celery tasks for async processing
- Management commands for setup and operations
- Django admin interface
- Multi-realm support
- Conflict resolution strategies (last_write_wins, source_wins, manual)
- Comprehensive test suite
- CI/CD pipeline with GitHub Actions
- Documentation (SRS, Architecture)

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- OAuth tokens encrypted at rest
- Webhook signature verification (HMAC-SHA256)
- Sensitive data masking in logs

## [0.1.0] - 2026-08-XX

### Added
- Initial release
- Core sync engine
- OAuth management
- Rate limiting
- Idempotency
- Audit logging
- Webhook support
- Celery integration
- Management commands
- Admin interface
- Multi-realm support
- Conflict resolution
- Test suite
- Documentation

[Unreleased]: https://github.com/mojnu/django-quickbooks-sync/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mojnu/django-quickbooks-sync/releases/tag/v0.1.0
