"""Application layer — use cases that orchestrate domain + repositories.

Pattern: Service Layer. Each service is a thin coordinator that:
  1. Loads aggregates via repositories
  2. Invokes domain methods to enforce invariants
  3. Persists changes via repositories
  4. Publishes domain events

Services are stateless and request-scoped via FastAPI Depends().
"""
