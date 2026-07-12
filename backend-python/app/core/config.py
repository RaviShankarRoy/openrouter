"""Configuration via pydantic-settings — env vars validated at startup."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- Common ----------
    environment: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "info"
    service_version: str = "0.1.0"

    # ---------- Server ----------
    backend_http_port: int = 8000
    backend_grpc_port: int = 50051
    backend_metrics_port: int = 9092
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # ---------- Database ----------
    postgres_dsn: str = "postgresql+asyncpg://openrouter:dev_only_password@localhost:5432/openrouter"
    postgres_pool_min: int = 5
    postgres_pool_max: int = 20

    # ---------- Redis ----------
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 50

    # ---------- NATS ----------
    nats_url: str = "nats://localhost:4222"
    nats_stream: str = "GATEWAY_EVENTS"

    # ---------- S3 ----------
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: SecretStr = SecretStr("openrouter")
    s3_secret_key: SecretStr = SecretStr("dev_only_password")
    s3_bucket: str = "openrouter-media"
    s3_region: str = "us-east-1"

    # ---------- Auth ----------
    secret_key: SecretStr = SecretStr("dev_only_change_in_prod_min_32_chars_long")
    argon2_time_cost: int = 3
    argon2_memory_cost_kb: int = 65_536  # 64MB per DRD SE-004
    argon2_parallelism: int = 4
    api_key_prefix: str = "sk-or-v1-"

    # ---------- Stripe ----------
    stripe_api_key: SecretStr = SecretStr("sk_test_replace_me")
    stripe_webhook_secret: SecretStr = SecretStr("whsec_replace_me")

    # ---------- Provider keys ----------
    openai_api_key: SecretStr = SecretStr("")
    anthropic_api_key: SecretStr = SecretStr("")
    google_api_key: SecretStr = SecretStr("")
    # OpenAI-compatible aggregators (Gemma 4, Qwen 3.x, Llama, etc.).
    together_api_key: SecretStr = SecretStr("")
    fireworks_api_key: SecretStr = SecretStr("")
    ollama_api_key: SecretStr = SecretStr("ollama")  # Ollama ignores it.

    # ---------- Semantic routing (DRD RT-002, §9.1) ----------
    routing_config_path: str = "./configs/routing.yaml"

    # ---------- OAuth ----------
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")

    # ---------- Observability ----------
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "backend-python"
    otel_traces_sampler_arg: float = 0.01

    # ---------- Free tier defaults (DRD RL-004) ----------
    free_tier_rpm: int = 20
    free_tier_daily_requests: int = 50


@lru_cache
def _get_settings() -> Settings:
    return Settings()


# Module-level singleton; safe because Settings is read-only after init.
settings: Settings = _get_settings()
