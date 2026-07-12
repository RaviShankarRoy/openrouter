# Cross-stack orchestration. Per-stack Makefiles live under each service directory.

.DEFAULT_GOAL := help
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

ENV ?= dev
COMPOSE = docker compose

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} \
	  /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ---------- Tooling ----------

.PHONY: check-tools
check-tools: ## Verify required toolchain versions
	@command -v go         >/dev/null || { echo "Missing: go 1.24+"; exit 1; }
	@command -v python3.12 >/dev/null || command -v python3 >/dev/null || { echo "Missing: python 3.12+"; exit 1; }
	@command -v node       >/dev/null || { echo "Missing: node 20+"; exit 1; }
	@command -v docker     >/dev/null || { echo "Missing: docker"; exit 1; }
	@command -v uv         >/dev/null || echo "WARN: uv not installed (https://docs.astral.sh/uv/)"
	@command -v pnpm       >/dev/null || echo "WARN: pnpm not installed"
	@echo "All required tools present."

# ---------- Local infra ----------

.PHONY: up down logs ps
up: ## Start postgres, redis, nats, minio
	$(COMPOSE) up -d

down: ## Stop local infra
	$(COMPOSE) down

logs: ## Tail local infra logs
	$(COMPOSE) logs -f --tail=100

ps: ## List local infra status
	$(COMPOSE) ps

# ---------- Codegen ----------

PROTO_DIR := shared/proto
PROTO_FILES := \
  $(PROTO_DIR)/auth/v1/auth.proto \
  $(PROTO_DIR)/routing/v1/routing.proto \
  $(PROTO_DIR)/usage/v1/usage.proto
PY_VENV := backend-python/.venv/bin/python
PY_GEN := backend-python/app/infrastructure/grpc/gen

.PHONY: codegen
codegen: proto codegen-frontend ## Run all code generators (proto + openapi)

.PHONY: codegen-frontend
codegen-frontend: ## Generate OpenAPI TypeScript types for the frontend
	$(MAKE) -C frontend-web codegen

.PHONY: proto proto-go proto-py proto-clean
proto: proto-go proto-py ## Generate gRPC stubs for Go and Python
	@echo "proto: codegen complete"

proto-go: ## Generate Go gRPC stubs (output: gateway-go/internal/proto/...)
	@test -x $$HOME/go/bin/protoc-gen-go      || { echo "Missing: go install google.golang.org/protobuf/cmd/protoc-gen-go@latest"; exit 1; }
	@test -x $$HOME/go/bin/protoc-gen-go-grpc || { echo "Missing: go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest"; exit 1; }
	@PATH="$$HOME/go/bin:$$PATH" $(PY_VENV) -m grpc_tools.protoc \
	  -I $(PROTO_DIR) \
	  --go_out=. --go_opt=module=github.com/openrouter \
	  --go-grpc_out=. --go-grpc_opt=module=github.com/openrouter \
	  $(PROTO_FILES)

proto-py: ## Generate Python gRPC stubs (output: backend-python/app/infrastructure/grpc/gen/...)
	@mkdir -p $(PY_GEN)
	@$(PY_VENV) -m grpc_tools.protoc \
	  -I $(PROTO_DIR) \
	  --python_out=$(PY_GEN) \
	  --grpc_python_out=$(PY_GEN) \
	  $(PROTO_FILES)
	@touch $(PY_GEN)/__init__.py \
	       $(PY_GEN)/auth/__init__.py    $(PY_GEN)/auth/v1/__init__.py \
	       $(PY_GEN)/routing/__init__.py $(PY_GEN)/routing/v1/__init__.py \
	       $(PY_GEN)/usage/__init__.py   $(PY_GEN)/usage/v1/__init__.py
	@sed -i 's|^from auth\.v1 import|from app.infrastructure.grpc.gen.auth.v1 import|'       $(PY_GEN)/auth/v1/auth_pb2_grpc.py       2>/dev/null || true
	@sed -i 's|^from routing\.v1 import|from app.infrastructure.grpc.gen.routing.v1 import|' $(PY_GEN)/routing/v1/routing_pb2_grpc.py 2>/dev/null || true
	@sed -i 's|^from usage\.v1 import|from app.infrastructure.grpc.gen.usage.v1 import|'     $(PY_GEN)/usage/v1/usage_pb2_grpc.py     2>/dev/null || true

proto-clean: ## Remove generated proto files
	rm -rf gateway-go/internal/proto $(PY_GEN)

# ---------- Database ----------

.PHONY: migrate migrate-create migrate-down
migrate: ## Apply database migrations
	$(MAKE) -C backend-python migrate

migrate-create: ## Create new migration: NAME=add_foo
	$(MAKE) -C backend-python migrate-create NAME=$(NAME)

migrate-down: ## Roll back last migration (dev only)
	$(MAKE) -C backend-python migrate-down

# ---------- Dev ----------

.PHONY: dev-gateway dev-backend dev-frontend dev-mock dev-all up-native up-docker down-docker
dev-gateway: ## Run Go gateway with hot reload
	$(MAKE) -C gateway-go dev

dev-backend: ## Run FastAPI with auto-reload
	$(MAKE) -C backend-python dev

dev-frontend: ## Run Next.js dev server
	$(MAKE) -C frontend-web dev

dev-mock: ## Run mock provider server
	$(MAKE) -C tools/mock-providers dev

dev-all: ## Run everything in tmux (requires tmux)
	./scripts/dev-all.sh

# ---------- Single-command full-stack dev ----------
# Two paths exist on purpose:
#   up-native  → fast iteration, native toolchains required
#   up-docker  → zero toolchain install, slow first boot, near-prod parity

up-native: up ## Start infra + all app services natively (Procfile.dev via overmind/honcho)
	@if command -v overmind >/dev/null; then \
	  echo ">>> overmind start -f Procfile.dev"; \
	  overmind start -f Procfile.dev; \
	elif command -v honcho >/dev/null; then \
	  echo ">>> honcho -f Procfile.dev start"; \
	  honcho -f Procfile.dev start; \
	elif command -v foreman >/dev/null; then \
	  echo ">>> foreman start -f Procfile.dev"; \
	  foreman start -f Procfile.dev; \
	else \
	  echo "Install one of: overmind (brew install overmind), honcho (pip install honcho), foreman (gem install foreman)"; \
	  exit 1; \
	fi

up-docker: ## Start infra + all app services in containers (single command)
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up

down-docker: ## Tear down the docker-compose dev stack (keeps named volumes)
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml down

down-docker-clean: ## Tear down and wipe cached volumes (forces full reinstall next start)
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml down -v

# ---------- Build ----------

.PHONY: build build-go build-py build-web
build: build-go build-py build-web ## Build all stacks

build-go: ## Build Go gateway binary
	$(MAKE) -C gateway-go build

build-py: ## Build Python wheel
	$(MAKE) -C backend-python build

build-web: ## Build Next.js production bundle
	$(MAKE) -C frontend-web build

# ---------- Test ----------

.PHONY: test test-go test-py test-web
test: test-go test-py test-web ## Run all tests

test-go:
	$(MAKE) -C gateway-go test

test-py:
	$(MAKE) -C backend-python test

test-web:
	$(MAKE) -C frontend-web test

# ---------- Lint ----------

.PHONY: lint lint-go lint-py lint-web
lint: lint-go lint-py lint-web ## Lint all stacks

lint-go:
	$(MAKE) -C gateway-go lint

lint-py:
	$(MAKE) -C backend-python lint

lint-web:
	$(MAKE) -C frontend-web lint

# ---------- Docker ----------

.PHONY: docker docker-go docker-py docker-web docker-cli
docker: docker-go docker-py docker-web ## Build all docker images

docker-go:
	docker build -t openrouter/gateway-go:dev gateway-go

docker-py:
	docker build -t openrouter/backend-python:dev backend-python

docker-web:
	docker build -t openrouter/frontend-web:dev frontend-web

docker-cli:
	docker build -t openrouter/cli:dev cli

# ---------- Kubernetes ----------

.PHONY: k8s-apply k8s-delete k8s-diff
k8s-apply: ## Apply k8s manifests for ENV (default: dev)
	kubectl apply -k infrastructure/kubernetes/overlays/$(ENV)

k8s-delete:
	kubectl delete -k infrastructure/kubernetes/overlays/$(ENV)

k8s-diff:
	kubectl diff -k infrastructure/kubernetes/overlays/$(ENV) || true

# ---------- Load tests ----------

.PHONY: load-test
load-test: ## Run k6 load test against local gateway
	$(MAKE) -C tools/load-tests run

# ---------- Cleanup ----------

.PHONY: clean
clean: ## Clean all build artifacts
	$(MAKE) -C gateway-go clean
	$(MAKE) -C backend-python clean
	$(MAKE) -C frontend-web clean
