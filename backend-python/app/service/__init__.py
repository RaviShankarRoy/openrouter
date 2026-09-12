"""Service tier — use cases that orchestrate domain rules + repositories.

Pattern: Service Layer. Each service is a thin coordinator that:
  1. Loads aggregates via repositories
  2. Invokes domain methods to enforce invariants
  3. Persists changes via repositories
  4. Publishes domain events

Services are stateless and request-scoped via FastAPI Depends().

Tier rules: this tier may import from `app.service.domain` and `app.shared`, and
depends on the repository tier only through the Port interfaces declared in
`app.service.domain.repositories` — never by importing `app.repository` directly.
"""

from app.service.auth_service import AuthService, CreateKeyCommand, CreatedKey
from app.service.billing_service import BillingService, MeterUsageCommand

__all__ = [
    "AuthService",
    "BillingService",
    "CreateKeyCommand",
    "CreatedKey",
    "MeterUsageCommand",
]
