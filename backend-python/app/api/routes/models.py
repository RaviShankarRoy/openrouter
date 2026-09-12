"""Model catalog route — derives from the in-process registry (DRD MK-010, BL-011)."""
from __future__ import annotations

import importlib
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_provider_registry
from app.repository.providers.registry import ProviderRegistry

router = APIRouter()


class PricingView(BaseModel):
    input_per_million: float
    output_per_million: float
    cached_input_per_million: float | None = None


class ModelView(BaseModel):
    id: str
    provider: str
    modalities: list[str]
    pricing: PricingView


class ModelListResponse(BaseModel):
    data: list[ModelView]


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    registry: Annotated[ProviderRegistry, Depends(get_provider_registry)],
) -> ModelListResponse:
    """Catalog of currently registered models with pricing.

    Production reads from the `model_pricing` table cached in Redis; this
    route surfaces the bootstrap registry's per-adapter `_PRICING` map so the
    contract is testable today.
    """
    items: list[ModelView] = []
    for provider_name in registry.names():
        adapter = registry.get(provider_name)
        module = importlib.import_module(type(adapter).__module__)
        pricing_map = getattr(module, "_PRICING", {})
        for model_id, tier in pricing_map.items():
            items.append(
                ModelView(
                    id=f"{provider_name}/{model_id}",
                    provider=provider_name,
                    modalities=adapter.supported_modalities,
                    pricing=PricingView(
                        input_per_million=float(tier.input_per_million),
                        output_per_million=float(tier.output_per_million),
                        cached_input_per_million=(
                            float(tier.cached_input_per_million)
                            if tier.cached_input_per_million is not None
                            else None
                        ),
                    ),
                )
            )
    return ModelListResponse(data=items)
