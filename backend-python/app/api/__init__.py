"""API layer — driving adapters for HTTP and gRPC ingress.

Maps wire formats (FastAPI request/response, gRPC messages) to application use
cases. Holds no business logic. Authentication, RBAC, and audit logging are
expressed here as decorators / dependencies because they are cross-cutting
HTTP concerns, not domain rules.
"""
