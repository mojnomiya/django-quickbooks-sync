# Contributing to django-quickbooks-sync

Thank you for your interest in contributing to django-quickbooks-sync! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment (see below)
4. Create a branch for your changes
5. Make your changes
6. Run tests
7. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.10+
- Redis (for Celery)
- Git

### Setup Instructions

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/django-quickbooks-sync.git
cd django-quickbooks-sync

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev,test]"

# Run migrations
python manage.py migrate

# Run tests
pytest tests/
```

### Code Quality Tools

```bash
# Linting
ruff check src/ tests/

# Formatting
black src/ tests/

# Type checking
mypy src/quickbooks_sync/
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-entity-sync`
- `fix/rate-limit-handling`
- `docs/update-api-reference`
- `test/add-integration-tests`

### Code Style

- Follow PEP 8 for Python code
- Use Black for code formatting
- Use Ruff for linting
- Add type hints for new functions
- Write docstrings for public APIs

### Documentation

- Update documentation for any new features
- Add examples for complex functionality
- Update the changelog

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=quickbooks_sync --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test
pytest tests/unit/test_models.py::QuickBooksRealmTest::test_create_realm
```

### Writing Tests

- Write unit tests for new functions
- Write integration tests for new features
- Aim for 90%+ code coverage
- Use pytest fixtures for common test data
- Mock external dependencies

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
└── conftest.py    # Pytest configuration
```

## Documentation

### Types of Documentation

1. **Code Documentation**
   - Docstrings for all public functions and classes
   - Type hints for all parameters and return values

2. **User Documentation**
   - README.md - Quick start and usage
   - docs/ - Detailed documentation

3. **Developer Documentation**
   - Architecture documents
   - Contributing guidelines

### Documentation Standards

- Use clear, concise language
- Include code examples
- Keep documentation up-to-date
- Use proper Markdown formatting

## Pull Request Process

### Before Submitting

1. Ensure all tests pass
2. Run code quality checks
3. Update documentation
4. Update changelog
5. Rebase on main branch

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Tests pass
- [ ] No new warnings
```

### Review Process

1. Automated CI checks must pass
2. At least one maintainer approval required
3. Address all review comments
4. Squash commits before merging

## Style Guidelines

### Python Style

```python
# Good
def sync_entity(
    entity_type: str,
    entity_id: str,
    data: dict[str, Any],
) -> SyncLog:
    """
    Sync an entity with QuickBooks.

    Args:
        entity_type: Type of entity (e.g., 'Customer')
        entity_id: Entity ID
        data: Entity data

    Returns:
        SyncLog entry for this operation
    """
    pass

# Bad
def sync_entity(entity_type, entity_id, data):
    pass
```

### Git Commits

```bash
# Good
git commit -m "feat: add customer sync support"
git commit -m "fix: handle rate limit exceeded"
git commit -m "docs: update API reference"

# Bad
git commit -m "update code"
git commit -m "fix bug"
```

## Questions?

If you have questions about contributing, please:
1. Check the documentation
2. Search existing issues
3. Open a new issue if needed

Thank you for contributing!
