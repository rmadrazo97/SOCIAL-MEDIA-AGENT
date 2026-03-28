"""Artifact CRUD endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Artifact
from app.schemas.schemas import ArtifactCreate, ArtifactUpdate, ArtifactOut

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"], dependencies=[Depends(verify_password)])


@router.get("", response_model=list[ArtifactOut])
async def list_artifacts(
    account_id: uuid.UUID = None,
    artifact_type: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Artifact).order_by(desc(Artifact.created_at)).limit(50)
    if account_id:
        q = q.where(Artifact.account_id == account_id)
    if artifact_type:
        q = q.where(Artifact.artifact_type == artifact_type)
    if status:
        q = q.where(Artifact.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{artifact_id}", response_model=ArtifactOut)
async def get_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.post("", response_model=ArtifactOut, status_code=201)
async def create_artifact(data: ArtifactCreate, db: AsyncSession = Depends(get_db)):
    artifact = Artifact(
        id=uuid.uuid4(),
        account_id=data.account_id,
        artifact_type=data.artifact_type,
        title=data.title,
        content=data.content,
        metadata_json=data.metadata_json,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact


@router.patch("/{artifact_id}", response_model=ArtifactOut)
async def update_artifact(artifact_id: uuid.UUID, data: ArtifactUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if data.title is not None:
        artifact.title = data.title
    if data.content is not None:
        artifact.content = data.content
    if data.status is not None:
        artifact.status = data.status
    if data.metadata_json is not None:
        artifact.metadata_json = data.metadata_json
    await db.commit()
    await db.refresh(artifact)
    return artifact


@router.delete("/{artifact_id}", status_code=204)
async def delete_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    await db.delete(artifact)
    await db.commit()
