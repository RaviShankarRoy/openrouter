.DEFAULT_GOAL := help
SHELL := /bin/bash

PKG_MANAGER := pnpm

.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install dependencies
	$(PKG_MANAGER) install --frozen-lockfile

.PHONY: dev
dev: ## Run Next.js dev server (turbopack)
	$(PKG_MANAGER) dev

.PHONY: build
build: ## Build production bundle
	$(PKG_MANAGER) build

.PHONY: start
start: ## Run production server
	$(PKG_MANAGER) start

.PHONY: test
test: ## Run unit tests (vitest)
	$(PKG_MANAGER) test

.PHONY: test-e2e
test-e2e: ## Run Playwright e2e tests
	$(PKG_MANAGER) test:e2e

.PHONY: lint
lint: ## Lint with ESLint + typecheck
	$(PKG_MANAGER) lint
	$(PKG_MANAGER) typecheck

.PHONY: format
format: ## Format with Prettier
	$(PKG_MANAGER) format

.PHONY: codegen
codegen: ## Regenerate OpenAPI TS types
	$(PKG_MANAGER) codegen:openapi

.PHONY: docker
docker: ## Build production docker image
	docker build -t openrouter/frontend-web:dev .

.PHONY: clean
clean: ## Remove build artefacts
	rm -rf .next out coverage playwright-report test-results node_modules/.cache
