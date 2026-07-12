"""OpenRouter backend.

Layering follows Clean Architecture / DDD:

    api/             — driving adapter (FastAPI routes, gRPC servicers)
    application/     — use cases, services, orchestrations
    domain/          — entities, value objects, domain events, errors
    infrastructure/  — driven adapters (DB, Redis, providers, Stripe, S3, NATS)
    core/            — config, logging, security primitives shared by all layers

Dependency rule: outer layers import inner; inner never imports outer.
"""

__version__ = "0.1.0"
