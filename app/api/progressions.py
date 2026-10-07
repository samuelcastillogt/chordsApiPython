from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.schemas import (
    ProgressionCreateRequest,
    ProgressionListResponse,
    ProgressionResponse,
    ProgressionUpdateRequest,
)
from app.core.security import get_current_user, get_optional_user
from app.domain.catalog import find_chord
from app.domain.theory import parse_key
from app.repositories import ProgressionRecord, Repository, UserRecord, get_repository

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


def serialize(progression: ProgressionRecord, user: UserRecord | None) -> dict:
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


async def owned_progression(progression_id: str, user: UserRecord, repository: Repository) -> ProgressionRecord:
    progression = await repository.get_progression(progression_id)
    if not progression or progression.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Progression not found")
    return progression


@router.get("/progressions", response_model=ProgressionListResponse)
async def list_progressions(user: UserRecord = Depends(get_current_user), repository: Repository = Depends(get_repository)):
    progressions = [serialize(item, user) for item in await repository.list_progressions(user.id)]
    return {"progressions": progressions, "total": len(progressions)}


@router.post("/progressions", response_model=ProgressionResponse, status_code=status.HTTP_201_CREATED)
async def create_progression(
    request: ProgressionCreateRequest,
    user: UserRecord = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
):
    progression = await repository.create_progression(
        ProgressionRecord(
            owner_id=user.id,
            name=request.name.strip(),
            chords=validate_chords(request.chords),
            tonality=validate_tonality(request.tonality),
            is_public=request.isPublic,
            source=request.source,
        )
    )
    return serialize(progression, user)


@router.get("/progressions/{progression_id}", response_model=ProgressionResponse)
async def get_progression(
    progression_id: str,
    user: UserRecord | None = Depends(get_optional_user),
    repository: Repository = Depends(get_repository),
):
    progression = await repository.get_progression(progression_id)
    is_owner = progression is not None and user is not None and progression.owner_id == user.id
    if not progression or not (progression.is_public or is_owner):
        raise HTTPException(status_code=404, detail="Progression not found")
    return serialize(progression, user)


@router.put("/progressions/{progression_id}", response_model=ProgressionResponse)
async def update_progression(
    progression_id: str,
    request: ProgressionUpdateRequest,
    user: UserRecord = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
):
    progression = await owned_progression(progression_id, user, repository)
    changes: dict = {}
    if request.name is not None:
        changes["name"] = request.name.strip()
    if request.chords is not None:
        changes["chords"] = validate_chords(request.chords)
    if request.tonality is not None:
        changes["tonality"] = validate_tonality(request.tonality)
    if request.isPublic is not None:
        changes["is_public"] = request.isPublic
    updated = await repository.update_progression(replace(progression, **changes))
    return serialize(updated, user)


@router.delete("/progressions/{progression_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_progression(
    progression_id: str,
    user: UserRecord = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
):
    await owned_progression(progression_id, user, repository)
    await repository.delete_progression(progression_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
