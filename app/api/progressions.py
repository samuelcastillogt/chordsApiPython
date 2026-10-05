from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ProgressionCreateRequest,
    ProgressionListResponse,
    ProgressionResponse,
    ProgressionUpdateRequest,
)
from app.core.security import get_current_user, get_optional_user
from app.db import get_session
from app.domain.catalog import find_chord
from app.domain.theory import parse_key
from app.models import Progression, User

router = APIRouter()


def validate_chords(chords: list[str]) -> list[str]:
    return [find_chord(chord).id for chord in chords]


def validate_tonality(tonality: str | None) -> str | None:
    if tonality is None:
        return None
    key = parse_key(tonality)
    if not key:
        raise HTTPException(status_code=400, detail=f"Unknown tonality: {tonality}")
    return key.id


def serialize(progression: Progression, user: User | None) -> dict:
    return {
        "id": progression.id,
        "name": progression.name,
        "chords": progression.chords,
        "tonality": progression.tonality,
        "isPublic": progression.is_public,
        "isOwner": user is not None and progression.owner_id == user.id,
        "source": progression.source,
        "createdAt": progression.created_at.isoformat(),
        "updatedAt": progression.updated_at.isoformat(),
    }


async def owned_progression(progression_id: str, user: User, session: AsyncSession) -> Progression:
    progression = await session.get(Progression, progression_id)
    if not progression or progression.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Progression not found")
    return progression


@router.get("/progressions", response_model=ProgressionListResponse)
async def list_progressions(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(
        select(Progression).where(Progression.owner_id == user.id).order_by(Progression.updated_at.desc())
    )
    progressions = [serialize(row, user) for row in rows]
    return {"progressions": progressions, "total": len(progressions)}


@router.post("/progressions", response_model=ProgressionResponse, status_code=status.HTTP_201_CREATED)
async def create_progression(
    request: ProgressionCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    progression = Progression(
        owner_id=user.id,
        name=request.name.strip(),
        chords=validate_chords(request.chords),
        tonality=validate_tonality(request.tonality),
        is_public=request.isPublic,
        source=request.source,
    )
    session.add(progression)
    await session.commit()
    await session.refresh(progression)
    return serialize(progression, user)


@router.get("/progressions/{progression_id}", response_model=ProgressionResponse)
async def get_progression(
    progression_id: str,
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    progression = await session.get(Progression, progression_id)
    is_owner = progression is not None and user is not None and progression.owner_id == user.id
    if not progression or not (progression.is_public or is_owner):
        raise HTTPException(status_code=404, detail="Progression not found")
    return serialize(progression, user)


@router.put("/progressions/{progression_id}", response_model=ProgressionResponse)
async def update_progression(
    progression_id: str,
    request: ProgressionUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    progression = await owned_progression(progression_id, user, session)
    if request.name is not None:
        progression.name = request.name.strip()
    if request.chords is not None:
        progression.chords = validate_chords(request.chords)
    if request.tonality is not None:
        progression.tonality = validate_tonality(request.tonality)
    if request.isPublic is not None:
        progression.is_public = request.isPublic
    await session.commit()
    await session.refresh(progression)
    return serialize(progression, user)


@router.delete("/progressions/{progression_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_progression(
    progression_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    progression = await owned_progression(progression_id, user, session)
    await session.delete(progression)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
