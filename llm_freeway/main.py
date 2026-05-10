from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.providers.registry import registry
from app.providers.openrouter import OpenRouterProvider
from app.providers.groq import GroqProvider
from app.providers.gemini import GeminiProvider
from app.providers.cohere import CohereProvider
from app.providers.cloudflare import CloudflareProvider
from app.providers.hyperbolic import HyperbolicProvider
from app.providers.sambanova import SambaNovaProvider
from app.providers.scaleway import ScalewayProvider
from app.providers.mistral import MistralProvider
from app.providers.cerebras import CerebrasProvider
from app.providers.kluster import KlusterProvider
from app.providers.github import GitHubProvider
from app.providers.nvidia import NVIDIAProvider
from app.routers import providers, models, chat, continuechat


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.register(OpenRouterProvider())
    registry.register(GroqProvider())
    registry.register(GeminiProvider())
    registry.register(CohereProvider())
    registry.register(CloudflareProvider())
    registry.register(HyperbolicProvider())
    registry.register(SambaNovaProvider())
    registry.register(ScalewayProvider())
    registry.register(MistralProvider())
    registry.register(CerebrasProvider())
    registry.register(KlusterProvider())
    registry.register(GitHubProvider())
    registry.register(NVIDIAProvider())
    yield


app = FastAPI(
    title="LLM-Freeway",
    description="Multi-provider LLM API gateway with automatic fallback",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(providers.router, tags=["providers"])
app.include_router(models.router, tags=["models"])
app.include_router(chat.router, tags=["chat"])
app.include_router(continuechat.router, tags=["chat"])


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "providers": len(registry.list_all()),
        "configured": len(registry.list_configured()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=4545, reload=True)
