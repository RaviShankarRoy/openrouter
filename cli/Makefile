.DEFAULT_GOAL := help
SHELL := /bin/bash

PKG := @openrouter/cli

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install dependencies
	npm install

.PHONY: dev
dev: ## Run CLI from source via tsx (passes args after `--`)
	npm run dev -- $(ARGS)

.PHONY: build
build: ## Bundle to dist/cli.js with shebang
	npm run build

.PHONY: test
test: ## Run vitest suite
	npm run test

.PHONY: test-watch
test-watch: ## Watch-mode tests
	npm run test:watch

.PHONY: lint
lint: ## ESLint over src + tests
	npm run lint

.PHONY: typecheck
typecheck: ## Strict TypeScript check (no emit)
	npm run typecheck

.PHONY: clean
clean: ## Remove build artifacts
	npm run clean

.PHONY: docker
docker: ## Build the docker image (target < 100MB)
	docker build -t openrouter/cli:dev .

.PHONY: link
link: build ## npm link for local global install
	npm link

.PHONY: publish-dry
publish-dry: build ## Dry-run npm publish
	npm publish --dry-run --access public
