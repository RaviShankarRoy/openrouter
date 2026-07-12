"""Infrastructure layer — concrete implementations of domain interfaces.

Modules here own all I/O: PostgreSQL, Redis, NATS, S3, Stripe, provider HTTP.
Domain layer never imports from here directly — only via Port interfaces.
"""
