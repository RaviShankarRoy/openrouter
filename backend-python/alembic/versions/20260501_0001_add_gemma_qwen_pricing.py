"""add Gemma 4 and Qwen 3.x pricing rows

Revision ID: 20260501_0001
Revises: 20260426_0000
Create Date: 2026-05-01 00:00:00

Seeds the model_pricing table for the new Gemma 4 (Apache 2.0) and Qwen 3.x
(Apache 2.0) catalog entries surfaced by /api/v1/models, the frontend
marketplace, and the CLI `models list` command. Idempotent — safe to re-run.
"""
from __future__ import annotations

from alembic import op

revision = "20260501_0001"
down_revision = "20260426_0000"
branch_labels = None
depends_on = None

# (model_key, provider, input/M, output/M, context_window, modalities_json)
_ROWS: list[tuple[str, str, str, str, int, str]] = [
    # Gemma 4 — Apache 2.0, multimodal (text/image/audio/video) + tools.
    ("google/gemma-4-31b",     "gemma", "0.30", "0.50", 256000,
     '["text","image","audio","video","tools"]'),
    ("google/gemma-4-26b-moe", "gemma", "0.20", "0.40", 256000,
     '["text","image","audio","video","tools"]'),
    ("google/gemma-4-e4b",     "gemma", "0.05", "0.10", 128000,
     '["text","image"]'),
    ("google/gemma-4-e2b",     "gemma", "0.02", "0.05", 128000,
     '["text"]'),
    # Qwen 3.x — Apache 2.0, text + tools.
    ("qwen/qwen3.6-27b",       "qwen",  "0.20", "0.60", 128000,
     '["text","tools"]'),
    ("qwen/qwen3.6-35b-a3b",   "qwen",  "0.27", "0.85", 128000,
     '["text","tools"]'),
    ("qwen/qwen3.5-35b-a3b",   "qwen",  "0.27", "0.85", 128000,
     '["text","tools"]'),
    ("qwen/qwen3.5-122b-a10b", "qwen",  "0.60", "1.80", 128000,
     '["text","tools"]'),
]


def upgrade() -> None:
    for model_key, provider, in_per_m, out_per_m, ctx, mods in _ROWS:
        op.execute(
            f"""
            INSERT INTO model_pricing
              (model_key, provider, input_per_million, output_per_million,
               context_window, modalities, active)
            VALUES
              ('{model_key}', '{provider}', {in_per_m}, {out_per_m},
               {ctx}, '{mods}'::jsonb, true)
            ON CONFLICT (model_key) DO NOTHING
            """
        )


def downgrade() -> None:
    keys = ",".join(f"'{r[0]}'" for r in _ROWS)
    op.execute(f"DELETE FROM model_pricing WHERE model_key IN ({keys})")
