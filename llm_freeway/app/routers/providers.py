from fastapi import APIRouter

from app.providers.registry import registry
from app.schemas import ProviderInfo

router = APIRouter()


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers():
    providers = registry.list_all()
    result = []
    for p in providers:
        try:
            models = await p.list_models()
            count = len(models)
        except Exception:
            count = 0
        result.append(
            ProviderInfo(
                name=p.name,
                configured=p.configured,
                models_count=count,
            )
        )
    return result
