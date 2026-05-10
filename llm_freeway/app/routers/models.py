from fastapi import APIRouter, HTTPException

from app.providers.registry import registry
from app.schemas import ModelInfo

router = APIRouter()


@router.get("/models/{provider}", response_model=list[ModelInfo])
async def list_models_for_provider(provider: str):
    prov = registry.get(provider)
    if not prov:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown provider: {provider}",
        )
    try:
        models = await prov.list_models()
        return models
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch models for {provider}: {e}",
        )
