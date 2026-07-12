# Shared Contracts

Single source of truth for cross-stack APIs. Both Go and Python regenerate code from these on CI — never edit generated code by hand.

## Contents

| Path | Generates |
|---|---|
| [`proto/`](proto/) | Internal Go↔Python gRPC. Codegen target: `make proto` |
| [`openapi/openapi.yaml`](openapi/openapi.yaml) | Public API spec. Codegen targets: TS SDK, Python types, Go server stubs |

## Code generation

```bash
# Proto → Go + Python
make proto

# OpenAPI → TS SDK
make openapi-ts

# OpenAPI → Python types (only request/response models, not server)
make openapi-py
```

Outputs land in `gen/` subdirectories (gitignored). CI fails the build if generated files differ from a clean regenerate — keeps the spec authoritative.
