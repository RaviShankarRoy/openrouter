"""Repository tier — concrete implementations of the domain Port interfaces.

Modules here own all I/O: PostgreSQL, Redis, NATS, S3, Stripe, provider HTTP,
Celery, and the generated gRPC stubs.

The aggregate repositories sit directly in this package (`api_keys`, `credits`,
`organizations`, `usage`, `users`, `video_jobs`); each one:
  - Takes an AsyncSession in __init__
  - Translates between ORM models and domain entities
  - Exposes only the methods declared in the matching domain Port

Tier rules: this is the lowest tier. It may import `app.shared` and the Port
definitions in `app.service.domain.repositories` that it implements, but never
the service tier's use cases or anything in `app.api`.
"""
