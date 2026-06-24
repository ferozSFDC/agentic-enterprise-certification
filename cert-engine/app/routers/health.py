"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness():
    """Is the process running?"""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Is the database connected and the item bank loaded?"""
    try:
        result = await db.execute(
            text("SELECT COUNT(*) FROM items WHERE status = 'active'")
        )
        active_items = result.scalar_one()
        if active_items == 0:
            return {"status": "degraded", "reason": "no active items in bank"}
        return {"status": "ok", "active_items": active_items}
    except Exception as e:
        return {"status": "unhealthy", "reason": str(e)}
