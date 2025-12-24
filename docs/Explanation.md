# License Service - Technical Explanation

## Problem Statement

group.one operates multiple WordPress-focused brands (WP Rocket, Imagify, RankMath, BackWPup, RocketCDN, WP.one) that each manage their own licensing. This creates data silos and duplicate effort across brands.

The Centralized License Service solves this by:
- Acting as single source of truth for all license data across brands
- Providing APIs for brand systems to provision and manage licenses
- Providing APIs for end-user products (plugins, apps) to activate and validate licenses
- Supporting cross-brand customer queries while maintaining tenant isolation

## Architecture and Design

### Clean Architecture with Service Layer

```
┌─────────────────────────────────────────────────────────────┐
│                        Views/API                            │
│  Thin controllers - HTTP handling, input validation         │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                       Services                              │
│  Business logic - framework agnostic, unit testable         │
│  LicenseProvisioningService, LicenseActivationService       │
│  LicenseStatusService, LicenseQueryService                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Repositories                             │
│  Data access abstraction via Protocol interfaces            │
│  Django ORM implementations injected at runtime             │
└─────────────────────────────────────────────────────────────┘
```

Services receive repository interfaces (Protocols) via constructor injection. This decouples business logic from Django, enabling unit tests with mock repositories.

### Data Model

```
Brand (tenant)
├── id, name, slug, api_key_hash, is_active
└── Product
    ├── id, name, slug, default_max_seats, is_active
    └── License
        ├── id, status, expires_at, max_seats
        └── Activation
            └── id, instance_id, instance_name, is_active

LicenseKey (customer-facing)
├── id, key, customer_email, external_reference
└── License (multiple products per key)
```

### Multi-Tenancy

Shared database with tenant column approach:
- All brands share one database with `brand_id` foreign key
- Enables cross-brand queries (US6) while maintaining isolation
- Lower operational overhead than database-per-tenant

## Trade-offs and Decisions

### Django REST Framework vs FastAPI
Chose DRF because:
- Mature ecosystem with built-in admin interface
- Strong ORM integration for rapid development
- Assignment recommended Django

Trade-off: Synchronous framework, but license validation isn't high-throughput enough to require async.

### Repository Pattern
Added abstraction between services and Django ORM:
- Pro: Services testable without database
- Pro: Can swap data layer (e.g., to SQLAlchemy) without changing business logic
- Con: More boilerplate code

Justified for long-term maintainability of a critical service.

### API Key Authentication
Custom header (`X-Brand-Api-Key: slug:secret`) instead of OAuth2:
- Simpler for server-to-server integrations
- SHA-256 hashed storage
- Per-brand isolation

OAuth2 considered but adds complexity unnecessary for backend-to-backend communication.

### Scaling Plan

**Current state**: Single PostgreSQL instance, stateless Django application.

**Horizontal scaling**:
- Application is stateless - add instances behind load balancer
- Database read replicas for query-heavy workloads

**Caching layer**:
- Add Redis for license status caching (most frequent query)
- Cache invalidation on license updates

**Database scaling**:
- Connection pooling (PgBouncer)
- Read replicas for US6 cross-brand queries
- Table partitioning by brand_id if data grows significantly

**Async processing**:
- Add Celery for webhook notifications
- Background license expiration processing

## User Story Implementation

| Story | Status | Implementation |
|-------|--------|----------------|
| US1: Brand provisions license | Implemented | `POST /api/v1/brands/{id}/license-keys/` creates key with licenses |
| US2: License lifecycle | Designed only | `LicenseStatus` enum (valid/suspended/cancelled) in model; API endpoints not exposed |
| US3: Product activates license | Implemented | `POST /api/v1/licenses/activate/` with seat enforcement |
| US4: Check license status | Implemented | `GET /api/v1/licenses/status/` returns validity and seat count |
| US5: Deactivate seat | Implemented | `POST /api/v1/licenses/deactivate/` frees seat |
| US6: Query by email | Implemented | `GET /api/v1/licenses/by-email/` cross-brand query (authenticated) |

**US2 not implemented**: Lifecycle state transitions (suspend/resume/cancel) are modeled but not exposed via API. The data model supports it with the `LicenseStatus` enum and `update_status` repository method. Prioritized core activation flow over lifecycle management within time constraints.

## How to Run Locally

### Prerequisites
- Python 3.12+
- Docker and Docker Compose

### Environment Variables

Copy `.env.example` to `.env`:

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=license_service
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

### Option 1: Full Docker

```bash
cd license_service
cp .env.example .env
make up
make migrate
curl http://localhost:8000/health/
```

### Option 2: Local App + Docker PostgreSQL

```bash
cd license_service

# Start only PostgreSQL in Docker
docker compose up -d db

# Create virtual environment
make venv
source venv/bin/activate

# Setup environment
cp .env.example .env

# Run migrations locally
DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py migrate

# Start local development server
make run
```

Verify: `curl http://localhost:8000/health/`

### Sample Requests

**Create license key (brand authenticated):**
```bash
curl -X POST http://localhost:8000/api/v1/brands/{brand_id}/license-keys/ \
  -H "X-Brand-Api-Key: {brand_slug}:{secret}" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "user@example.com",
    "products": [{"product_id": "{uuid}", "expires_at": "2025-12-31T23:59:59Z"}]
  }'
```

**Activate license (public):**
```bash
curl -X POST http://localhost:8000/api/v1/licenses/activate/ \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "{key}",
    "product_slug": "wp-rocket",
    "instance_id": "https://example.com"
  }'
```

**Check license status (public):**
```bash
curl "http://localhost:8000/api/v1/licenses/status/?license_key={key}&product_slug=wp-rocket"
```

**Deactivate license (public):**
```bash
curl -X POST http://localhost:8000/api/v1/licenses/deactivate/ \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "{key}",
    "product_slug": "wp-rocket",
    "instance_id": "https://example.com"
  }'
```

**Query by email (brand authenticated):**
```bash
curl "http://localhost:8000/api/v1/licenses/by-email/?email=user@example.com" \
  -H "X-Brand-Api-Key: {brand_slug}:{secret}"
```

## Known Limitations and Next Steps

### Limitations
1. **US2 not implemented** - Lifecycle transitions designed but API not exposed
2. **No webhook notifications** - Brands must poll for updates
3. **No caching** - Every status check hits database
4. **No async processing** - All operations synchronous

### Next Steps
1. Expose lifecycle API endpoints (suspend/resume/cancel)
2. Add Redis caching for status checks
3. Implement webhook notifications for license events
4. Add Celery for background processing (expiration checks, audit logging)
5. Add Prometheus metrics for observability
