from fastapi import APIRouter, HTTPException

from app.schemas import ContinueChatRequest, ChatResponse
from app.services.fallback_service import continue_chat, AllProvidersExhausted

router = APIRouter()


@router.post("/continuechat", response_model=ChatResponse)
async def continue_chat_endpoint(req: ContinueChatRequest):
    try:
        response = await continue_chat(
            messages=req.messages,
            system_prompt=req.system_prompt,
            memory=req.memory,
            session_id=req.session_id,
            provider_priority=req.provider_priority,
        )
        return response
    except AllProvidersExhausted as e:
        raise HTTPException(
            status_code=507,
            detail={
                "error": "All providers/models exhausted",
                "attempts": e.errors,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
