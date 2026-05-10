from fastapi import APIRouter, HTTPException

from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import chat as chat_service
from app.providers.base import RateLimitError, AuthError, ProviderError

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        response = await chat_service(
            provider_name=req.provider,
            model=req.model,
            messages=req.messages,
            system_prompt=req.system_prompt,
            memory=req.memory,
            session_id=req.session_id,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
