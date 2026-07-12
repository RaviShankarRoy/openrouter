# k6 load tests — wrapper around `k6 run` with consistent env handling.

K6        ?= k6
BASE_URL  ?= http://localhost:8080
API_TOKEN ?= sk-or-v1-loadtest0000000000000000000000000000000000000000000000000000
K6_OUT    ?=
ENV_FLAGS  = -e BASE_URL=$(BASE_URL) -e API_TOKEN=$(API_TOKEN)

.PHONY: help smoke run load stress spike soak streaming gemma-qwen gemma-qwen-stream

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

smoke: ## 1 VU, 30s — sanity check
	$(K6) run $(K6_OUT) $(ENV_FLAGS) k6/scenarios/smoke.js

run: load ## Alias for `load`

load: ## 5K RPS sustained for 5min — proves NFR-005 baseline
	$(K6) run $(K6_OUT) $(ENV_FLAGS) k6/scenarios/load.js

stress: ## Ramp to 15K RPS — find the breaking point
	$(K6) run $(K6_OUT) $(ENV_FLAGS) k6/scenarios/stress.js

spike: ## 0 -> 10K -> 0 in 60s — burst tolerance
	$(K6) run $(K6_OUT) $(ENV_FLAGS) k6/scenarios/spike.js

soak: ## 2K RPS for 1 hour — leak detection
	$(K6) run $(K6_OUT) $(ENV_FLAGS) k6/scenarios/soak.js

streaming: ## SSE-specific test — proves NFR-003
	$(K6) run $(K6_OUT) $(ENV_FLAGS) k6/scenarios/streaming.js

gemma-qwen: ## Open-weight catalog (Gemma 4 + Qwen 3.6) — non-streaming
	$(K6) run $(K6_OUT) $(ENV_FLAGS) k6/scenarios/gemma_qwen.js

gemma-qwen-stream: ## Open-weight catalog — streaming variant
	$(K6) run $(K6_OUT) $(ENV_FLAGS) -e STREAM=1 k6/scenarios/gemma_qwen.js
