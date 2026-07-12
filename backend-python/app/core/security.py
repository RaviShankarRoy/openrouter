"""Cryptographic primitives — argon2id key hashing, JWT signing.

Pure functions; no I/O. Importable from any layer.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt

from app.core.config import settings

# DRD SE-004 + AK-002 — argon2id with documented cost.
_hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost_kb,
    parallelism=settings.argon2_parallelism,
    hash_len=32,
    salt_len=16,
)


def hash_api_key(plaintext: str) -> str:
    """argon2id hash for at-rest storage. Never reversible."""
    return _hasher.hash(plaintext)


def verify_api_key(plaintext: str, stored_hash: str) -> bool:
    try:
        return _hasher.verify(stored_hash, plaintext)
    except VerifyMismatchError:
        return False


def sha256_lookup(plaintext: str) -> str:
    """SHA-256 hex digest. Used for the Redis lookup key — argon2 is too slow per request."""
    return hashlib.sha256(plaintext.encode()).hexdigest()


def generate_api_key() -> str:
    """Format per DRD AK-001: sk-or-v1-{64 random hex chars}."""
    return f"{settings.api_key_prefix}{secrets.token_hex(32)}"


# --- JWT for OAuth bearer tokens (DRD AK-006) ---


def encode_jwt(claims: dict, expires_in: timedelta = timedelta(hours=1)) -> str:
    payload = {
        **claims,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + expires_in,
    }
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm="HS256")


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=["HS256"])
