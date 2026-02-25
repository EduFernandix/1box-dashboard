"""Alert history API endpoints."""

from fastapi import APIRouter, Query
from sqlalchemy import select

from src.api.dependencies import DbSession
from src.models.database import AlertHistory
from src.models.schemas import AlertHistoryRead

router = APIRouter()


@router.get("/history", response_model=list[AlertHistoryRead])
async def alert_history(
    session: DbSession,
    limit: int = Query(50, ge=1, le=500, description="Number of alerts to return"),
    severity: str | None = Query(None, description="Filter by severity"),
) -> list[AlertHistoryRead]:
    """Get recent alert history, ordered by most recent first."""
    stmt = select(AlertHistory).order_by(
        AlertHistory.triggered_at.desc()
    )
    if severity:
        stmt = stmt.where(AlertHistory.severity == severity.lower())
    stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return [
        AlertHistoryRead.model_validate(r) for r in result.scalars().all()
    ]
