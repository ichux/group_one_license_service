# Do not remove this block. It is used by the 'help' rule when
# constructing the help output.
# help: License Service Makefile help
# help:

SHELL := /bin/bash

# ============================================================================
# Path Variables
# ============================================================================
PYTHON := python3
DOCKER_COMPOSE := docker compose

.PHONY: help
# help: help				- Please use "make <target>" where <target> is one of
help:
	@grep "^# help\:" Makefile | sed 's/\# help\: //' | sed 's/\# help\://'

# ============================================================================
# Environment Setup
# ============================================================================

.PHONY: env
# help: env				- copy .env.example to .env
env:
	@cp .env.example .env
	@echo "✅ Created .env from .env.example"

.PHONY: venv
# help: venv				- create virtual environment and install dev dependencies
venv:
	@$(PYTHON) -m venv venv
	@./venv/bin/pip install --upgrade pip
	@./venv/bin/pip install -r requirements/dev.txt
	@echo "✅ Virtual environment created. Activate with: source venv/bin/activate"

# ============================================================================
# Docker Commands
# ============================================================================

.PHONY: up
# help: up				- build and start all containers
up:
	@$(DOCKER_COMPOSE) up --build -d
	@echo "✅ Containers started. API available at http://localhost:8000"

.PHONY: down
# help: down				- stop and remove all containers
down:
	@$(DOCKER_COMPOSE) down
	@echo "✅ Containers stopped"

.PHONY: logs
# help: logs				- show container logs (follow mode)
logs:
	@$(DOCKER_COMPOSE) logs -f

.PHONY: logs-app
# help: logs-app			- show app container logs (follow mode)
logs-app:
	@$(DOCKER_COMPOSE) logs -f app

.PHONY: status
# help: status				- show container status
status:
	@$(DOCKER_COMPOSE) ps

.PHONY: shell
# help: shell				- open bash shell in app container
shell:
	@$(DOCKER_COMPOSE) exec app bash

.PHONY: dbshell
# help: dbshell				- open PostgreSQL shell
dbshell:
	@$(DOCKER_COMPOSE) exec db psql -U postgres -d license_service

# ============================================================================
# Django Commands
# ============================================================================

.PHONY: migrate
# help: migrate				- run database migrations
migrate:
	@$(DOCKER_COMPOSE) exec app python manage.py migrate

.PHONY: makemigrations
# help: makemigrations			- create new migrations
makemigrations:
	@$(DOCKER_COMPOSE) exec app python manage.py makemigrations

.PHONY: createsuperuser
# help: createsuperuser			- create Django admin superuser
createsuperuser:
	@$(DOCKER_COMPOSE) exec app python manage.py createsuperuser

.PHONY: collectstatic
# help: collectstatic			- collect static files
collectstatic:
	@$(DOCKER_COMPOSE) exec app python manage.py collectstatic --noinput

# ============================================================================
# Testing
# ============================================================================

.PHONY: test
# help: test				- run all tests in Docker
test:
	@$(DOCKER_COMPOSE) run --rm test

.PHONY: test-local
# help: test-local			- run all tests locally (requires venv)
test-local:
	@source venv/bin/activate && \
	DJANGO_SETTINGS_MODULE=config.settings.ci pytest -v

.PHONY: test-cov
# help: test-cov			- run tests with coverage report
test-cov:
	@source venv/bin/activate && \
	DJANGO_SETTINGS_MODULE=config.settings.ci pytest --cov=apps --cov-report=term-missing --cov-report=html
	@echo "✅ Coverage report generated: htmlcov/index.html"

.PHONY: test-unit
# help: test-unit			- run only unit tests
test-unit:
	@source venv/bin/activate && \
	DJANGO_SETTINGS_MODULE=config.settings.ci pytest tests/unit/ -v

.PHONY: test-integration
# help: test-integration		- run only integration tests
test-integration:
	@source venv/bin/activate && \
	DJANGO_SETTINGS_MODULE=config.settings.ci pytest tests/integration/ -v

# ============================================================================
# Linting & Code Quality
# ============================================================================

.PHONY: lint
# help: lint				- run all linting checks (black, isort, ruff)
lint:
	@source venv/bin/activate && \
	black --check . && \
	isort --check --profile black . && \
	ruff check .
	@echo "✅ All linting checks passed"

.PHONY: lint-docker
# help: lint-docker			- run linting checks in Docker
lint-docker:
	@$(DOCKER_COMPOSE) run --rm lint

.PHONY: format
# help: format				- auto-format code (black, isort)
format:
	@source venv/bin/activate && \
	black . && \
	isort --profile black .
	@echo "✅ Code formatted"

.PHONY: ruff-fix
# help: ruff-fix			- auto-fix ruff issues
ruff-fix:
	@source venv/bin/activate && \
	ruff check . --fix
	@echo "✅ Ruff issues fixed"

.PHONY: typecheck
# help: typecheck			- run mypy type checking
typecheck:
	@source venv/bin/activate && \
	mypy apps/ --ignore-missing-imports

# ============================================================================
# Security
# ============================================================================

.PHONY: security
# help: security			- run security scan (bandit)
security:
	@source venv/bin/activate && \
	bandit -r apps/ -c pyproject.toml
	@echo "✅ Security scan passed"

.PHONY: security-check
# help: security-check			- run all security checks (bandit + safety)
security-check:
	@source venv/bin/activate && \
	bandit -r apps/ -c pyproject.toml && \
	safety check -r requirements/base.txt --ignore 70612
	@echo "✅ All security checks passed"

# ============================================================================
# CI Pipeline (runs all checks)
# ============================================================================

.PHONY: ci
# help: ci				- run full CI pipeline locally (lint + security + test)
ci: lint security test-local
	@echo "✅ CI pipeline passed"

.PHONY: ci-docker
# help: ci-docker			- run full CI pipeline in Docker
ci-docker: lint-docker test
	@echo "✅ Docker CI pipeline passed"

# ============================================================================
# Development Helpers
# ============================================================================

.PHONY: run
# help: run				- run development server locally
run:
	@source venv/bin/activate && \
	DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py runserver

.PHONY: fresh
# help: fresh				- full reset: down, prune, up, migrate
fresh: down
	@docker volume prune -f
	@$(MAKE) up
	@sleep 5
	@$(MAKE) migrate
	@echo "✅ Fresh environment ready"

.PHONY: clean
# help: clean				- remove compiled Python files and caches
clean:
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Cleaned up compiled files and caches"

# ============================================================================
# API Documentation
# ============================================================================

.PHONY: schema
# help: schema				- generate OpenAPI schema
schema:
	@source venv/bin/activate && \
	python manage.py spectacular --file schema.yml
	@echo "✅ OpenAPI schema generated: schema.yml"

# ============================================================================
# Production
# ============================================================================

.PHONY: build-prod
# help: build-prod			- build production Docker image
build-prod:
	@docker build -t license-service:latest -f Dockerfile .
	@echo "✅ Production image built: license-service:latest"

.PHONY: check-ready
# help: check-ready			- check if service is ready (health check)
check-ready:
	@curl -s http://localhost:8000/health/ | python -m json.tool

# ============================================================================
# API Examples (no values)
# ============================================================================

.PHONY: api-examples
# help: api-examples			- show API call examples
api-examples:
	@echo "=== License Service API Examples ==="
	@echo ""
	@echo "Health Check:"
	@echo "  curl http://localhost:8000/health/"
	@echo ""
	@echo "Provision License Key (requires Brand API key):"
	@echo "  curl -X POST http://localhost:8000/api/v1/brands/{brand_id}/license-keys/ \\"
	@echo "    -H 'X-Brand-Api-Key: {brand_slug}:{secret}' \\"
	@echo "    -H 'Content-Type: application/json' \\"
	@echo "    -d '{\"customer_email\": \"{email}\", \"products\": [{\"product_id\": \"{uuid}\", \"expires_at\": \"{iso_datetime}\"}]}'"
	@echo ""
	@echo "Get License Key Details:"
	@echo "  curl http://localhost:8000/api/v1/brands/{brand_id}/license-keys/{key}/ \\"
	@echo "    -H 'X-Brand-Api-Key: {brand_slug}:{secret}'"
	@echo ""
	@echo "Add License to Existing Key:"
	@echo "  curl -X POST http://localhost:8000/api/v1/brands/{brand_id}/license-keys/{key}/licenses/ \\"
	@echo "    -H 'X-Brand-Api-Key: {brand_slug}:{secret}' \\"
	@echo "    -H 'Content-Type: application/json' \\"
	@echo "    -d '{\"product_id\": \"{uuid}\", \"expires_at\": \"{iso_datetime}\"}'"
	@echo ""
	@echo "Activate License (public endpoint):"
	@echo "  curl -X POST http://localhost:8000/api/v1/licenses/activate/ \\"
	@echo "    -H 'Content-Type: application/json' \\"
	@echo "    -d '{\"license_key\": \"{key}\", \"product_slug\": \"{slug}\", \"instance_id\": \"{url}\", \"instance_name\": \"{name}\"}'"
	@echo ""
	@echo "Deactivate License (public endpoint):"
	@echo "  curl -X POST http://localhost:8000/api/v1/licenses/deactivate/ \\"
	@echo "    -H 'Content-Type: application/json' \\"
	@echo "    -d '{\"license_key\": \"{key}\", \"product_slug\": \"{slug}\", \"instance_id\": \"{url}\"}'"
	@echo ""
	@echo "Check License Status (public endpoint):"
	@echo "  curl 'http://localhost:8000/api/v1/licenses/status/?license_key={key}&product_slug={slug}'"
	@echo ""
	@echo "Query Licenses by Email (requires Brand API key):"
	@echo "  curl 'http://localhost:8000/api/v1/licenses/by-email/?email={email}' \\"
	@echo "    -H 'X-Brand-Api-Key: {brand_slug}:{secret}'"
