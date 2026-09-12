.DEFAULT_GOAL := help
SHELL := /bin/bash

PYTHON ?= $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python3.12)
UV ?= uv

.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install deps via uv (recommended) or pip
	@if command -v $(UV) >/dev/null; then \
		$(UV) sync --extra dev; \
	else \
		$(PYTHON) -m venv .venv && .venv/bin/pip install -e '.[dev]'; \
	fi

.PHONY: dev
dev: ## Run FastAPI with auto-reload
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: prod
prod: ## Run with gunicorn (production worker model)
	$(PYTHON) -m gunicorn app.main:app \
	  --workers 4 --worker-class uvicorn.workers.UvicornWorker \
	  --bind 0.0.0.0:8000 --access-logfile - --error-logfile -

.PHONY: worker
worker: ## Run Celery worker
	$(PYTHON) -m celery -A app.repository.celery_app worker -l info

.PHONY: grpc-serve
grpc-serve: ## Run the standalone gRPC server (AuthService + RoutingService)
	$(PYTHON) -m app.grpc_main

.PHONY: beat
beat: ## Run Celery beat (scheduled tasks)
	$(PYTHON) -m celery -A app.repository.celery_app beat -l info

.PHONY: migrate
migrate: ## Apply Alembic migrations
	$(PYTHON) -m alembic upgrade head

.PHONY: migrate-create
migrate-create: ## Create new migration: NAME=description
	$(PYTHON) -m alembic revision --autogenerate -m "$(NAME)"

.PHONY: migrate-down
migrate-down: ## Roll back one migration (dev only)
	$(PYTHON) -m alembic downgrade -1

.PHONY: test
test: ## Run unit + integration tests
	$(PYTHON) -m pytest

.PHONY: test-unit
test-unit:
	$(PYTHON) -m pytest tests/unit

.PHONY: test-integration
test-integration:
	$(PYTHON) -m pytest tests/integration

.PHONY: lint
lint: ## Lint and type-check
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy app

.PHONY: fmt
fmt:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

.PHONY: build
build:
	$(PYTHON) -m pip wheel --no-deps -w dist .

.PHONY: clean
clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
