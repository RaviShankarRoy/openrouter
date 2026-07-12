# Mock provider server — DRD §23.2.
# Targets keep parity with backend-python/Makefile so devs do not relearn.

PYTHON ?= python3.12
PORT   ?= 9100
IMAGE  ?= openrouter/mock-providers:dev

.PHONY: help install dev test lint format docker docker-run clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install runtime + dev deps in current venv
	$(PYTHON) -m pip install -e ".[dev]"

dev: ## Run the mock providers server with autoreload on $(PORT)
	uvicorn src.main:app --host 0.0.0.0 --port $(PORT) --reload

test: ## Run pytest
	pytest -q

lint: ## Run ruff lint
	ruff check src tests

format: ## Run ruff format
	ruff format src tests

docker: ## Build container image (multi-stage, target < 200MB)
	docker build -t $(IMAGE) .

docker-run: ## Run container locally on $(PORT)
	docker run --rm -p $(PORT):9100 -e MOCK_PORT=9100 $(IMAGE)

clean: ## Remove caches
	rm -rf .pytest_cache .ruff_cache __pycache__ src/__pycache__ tests/__pycache__
