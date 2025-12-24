# License Service

Centralized License Service for group.one brands (WP Rocket, Imagify, RankMath, BackWPup, RocketCDN, WP.one).

## Overview

This service acts as the **single source of truth** for license lifecycle and entitlements across all brands in the group.one ecosystem.

### Features

- Multi-tenant architecture supporting multiple brands
- License key provisioning and management
- Product entitlement management
- License activation and seat management
- Cross-brand customer license queries
- RESTful API with OpenAPI documentation

## Architecture

The service implements **Clean Architecture** with a clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                      HTTP Layer (Views)                     │
│           Thin controllers, request/response handling       │
└─────────────────────────────────┬───────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────┐
│                     Service Layer                           │
│     Business logic, validation, orchestration               │
│     (LicenseProvisioningService, LicenseActivationService)  │
└─────────────────────────────────┬───────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────┐
│                   Repository Layer                          │
│      Data access abstraction via Protocol interfaces        │
│              (LicenseKeyRepository, etc.)                   │
└─────────────────────────────────┬───────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────┐
│                       Data Layer                            │
│            Django ORM models, database operations           │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Models | `apps/*/models.py` | Django ORM models |
| Repositories | `apps/licenses/repositories.py` | Protocol interfaces for data access |
| Django Repositories | `apps/licenses/repositories_django.py` | Django ORM implementations |
| Services | `apps/licenses/services.py` | Business logic (framework-agnostic) |
| Views | `apps/licenses/views.py` | HTTP request handlers |
| Serializers | `apps/licenses/serializers.py` | API input/output schemas |

### Benefits

- **Testability**: Services can be unit tested with mock repositories (no database)
- **Flexibility**: Repository implementations can be swapped (Django ORM, SQLAlchemy, etc.)
- **Maintainability**: Clear boundaries between layers
- **Framework Independence**: Business logic has no Django dependencies

## Quick Start

### With Docker (Recommended)

```bash
# Clone and setup
git clone <repository-url>
cd license_service
make env

# Start services
make up

# Run migrations
make migrate

# Check health
make check-ready
```

### Local Development

```bash
# Create virtual environment
make venv
source venv/bin/activate

# Setup environment
make env

# Run tests locally
make test-local

# Start development server
make run
```

### Using Makefile

```bash
make help              # Show all commands
make up                # Start Docker containers
make down              # Stop containers
make test              # Run tests in Docker
make test-local        # Run tests locally
make test-cov          # Run tests with coverage
make lint              # Run linting
make format            # Auto-format code
make security          # Run security scan
make ci                # Full CI pipeline
make api-examples      # Show API usage examples
```

## API Endpoints

### Authentication

Brand-authenticated endpoints require the `X-Brand-Api-Key` header:
```
X-Brand-Api-Key: {brand_slug}:{secret}
```

### Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health/` | No | Health check |
| POST | `/api/v1/brands/{id}/license-keys/` | Brand | Provision license key |
| GET | `/api/v1/brands/{id}/license-keys/{key}/` | Brand | Get license key details |
| POST | `/api/v1/brands/{id}/license-keys/{key}/licenses/` | Brand | Add license to key |
| POST | `/api/v1/licenses/activate/` | No | Activate license |
| POST | `/api/v1/licenses/deactivate/` | No | Deactivate license |
| GET | `/api/v1/licenses/status/` | No | Check license status |
| GET | `/api/v1/licenses/by-email/` | Brand | Query by email |

### API Examples

```bash
# Health check
curl http://localhost:8000/health/

# Provision license key
curl -X POST http://localhost:8000/api/v1/brands/{brand_id}/license-keys/ \
  -H 'X-Brand-Api-Key: {brand_slug}:{secret}' \
  -H 'Content-Type: application/json' \
  -d '{"customer_email": "{email}", "products": [{"product_id": "{uuid}", "expires_at": "{iso_datetime}"}]}'

# Get license key details
curl http://localhost:8000/api/v1/brands/{brand_id}/license-keys/{key}/ \
  -H 'X-Brand-Api-Key: {brand_slug}:{secret}'

# Add license to existing key
curl -X POST http://localhost:8000/api/v1/brands/{brand_id}/license-keys/{key}/licenses/ \
  -H 'X-Brand-Api-Key: {brand_slug}:{secret}' \
  -H 'Content-Type: application/json' \
  -d '{"product_id": "{uuid}", "expires_at": "{iso_datetime}"}'

# Activate license
curl -X POST http://localhost:8000/api/v1/licenses/activate/ \
  -H 'Content-Type: application/json' \
  -d '{"license_key": "{key}", "product_slug": "{slug}", "instance_id": "{url}", "instance_name": "{name}"}'

# Check license status
curl 'http://localhost:8000/api/v1/licenses/status/?license_key={key}&product_slug={slug}'

# Deactivate license
curl -X POST http://localhost:8000/api/v1/licenses/deactivate/ \
  -H 'Content-Type: application/json' \
  -d '{"license_key": "{key}", "product_slug": "{slug}", "instance_id": "{url}"}'

# Query licenses by email
curl 'http://localhost:8000/api/v1/licenses/by-email/?email={email}' \
  -H 'X-Brand-Api-Key: {brand_slug}:{secret}'
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Unit tests only (no database)
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v
```

### Test Architecture

- **Unit Tests** (`tests/unit/`): Test services with mocked repositories
- **Integration Tests** (`tests/integration/`): Test full API with database

## API Documentation

- Swagger UI: http://localhost:8000/api/schema/swagger-ui/
- ReDoc: http://localhost:8000/api/schema/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## Project Structure

```
license_service/
├── apps/
│   ├── core/                 # Shared utilities, authentication
│   │   ├── authentication.py # Brand API key auth
│   │   └── exceptions.py     # Custom exception handler
│   ├── brands/               # Brand and product models
│   │   └── models.py
│   └── licenses/             # License management
│       ├── models.py         # ORM models
│       ├── repositories.py   # Protocol interfaces
│       ├── repositories_django.py  # Django implementations
│       ├── services.py       # Business logic
│       ├── serializers.py    # API schemas
│       └── views.py          # HTTP handlers
├── config/
│   ├── settings/             # Django settings
│   │   ├── base.py          # Base settings
│   │   ├── dev.py           # Development
│   │   ├── ci.py            # CI/Testing
│   │   └── prod.py          # Production
│   └── urls.py
├── requirements/
│   ├── base.txt             # Core dependencies
│   ├── dev.txt              # Development tools
│   └── ci.txt               # CI dependencies
├── tests/
│   ├── unit/                # Service unit tests
│   └── integration/         # API integration tests
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## Security

- Rate limiting enabled (100/hour anonymous, 1000/hour authenticated)
- API key authentication with SHA-256 hashing
- Security headers in production (HSTS, X-Frame-Options, etc.)
- Bandit security scanning in CI

## Documentation

For detailed architectural decisions, design rationale, and implementation explanations, see [Explanation.md](docs/Explanation.md).

## License

MIT
