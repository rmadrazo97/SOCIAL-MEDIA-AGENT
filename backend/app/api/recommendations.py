from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Recommendation
from app.schemas.schemas import RecommendationOut, RecommendationUpdate

router = APIRouter(prefix="/api", tags=["recommendations"], dependencies=[Depends(verify_password)])


@router.get("/accounts/{account_id}/recommendations", response_model=list[RecommendationOut])
async def list_recommendations(
    account_id: UUID,
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Recommendation).where(Recommendation.account_id == account_id)
    if status:
        q = q.where(Recommendation.status == status)
    q = q.order_by(desc(Recommendation.priority), desc(Recommendation.created_at)).limit(50)
    result = await db.execute(q)
    return result.scalars().all()


@router.patch("/recommendations/{rec_id}", response_model=RecommendationOut)
async def update_recommendation(
    rec_id: UUID,
    data: RecommendationUpdate,
    db: AsyncSession = Depends(get_db),
):
    rec = await db.get(Recommendation, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec.status = data.status
    await db.commit()
    await db.refresh(rec)
    return rec
