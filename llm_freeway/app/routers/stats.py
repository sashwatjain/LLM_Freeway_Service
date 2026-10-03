from fastapi import APIRouter

from app.services.limit_tracker import limit_tracker

router = APIRouter()


@router.get("/stats")
async def usage_stats():
    return limit_tracker.get_usage_snapshot()

