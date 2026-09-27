from datetime import datetime, timezone

from fastapi import APIRouter

from app import __version__
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }