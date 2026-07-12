.DEFAULT_GOAL := help
SHELL := /bin/bash

BIN := bin/gateway
PKG := ./...

.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: dev
dev: ## Run with hot reload via air (install: go install github.com/air-verse/air@latest)
	air -c .air.toml

.PHONY: run
run: ## Run without reload
	go run ./cmd/gateway

.PHONY: build
build: ## Build static binary
	CGO_ENABLED=0 go build -trimpath -ldflags "-s -w -X main.version=$$(git describe --tags --always 2>/dev/null || echo dev)" -o $(BIN) ./cmd/gateway

.PHONY: test
test: ## Run unit tests
	go test -race -coverprofile=coverage.out -covermode=atomic $(PKG)

.PHONY: test-integration
test-integration: ## Run integration tests (needs testcontainers)
	go test -race -tags=integration $(PKG)

.PHONY: bench
bench: ## Run benchmarks
	go test -bench=. -benchmem -run=^$ $(PKG)

.PHONY: lint
lint: ## Lint via golangci-lint
	golangci-lint run

.PHONY: fmt
fmt:
	gofmt -s -w .
	goimports -w .

.PHONY: clean
clean:
	rm -rf bin coverage.out
