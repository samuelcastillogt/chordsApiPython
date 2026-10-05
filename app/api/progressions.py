from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, status

from app.api.schemas import (
    ProgressionCreateRequest,
    ProgressionListResponse,
    ProgressionResponse,
    ProgressionUpdateRequest,
)
from app.domain.chord import ChordNode

router = APIRouter()
_all_chords = ChordNode.build_all()
_progressions: dict[str, dict] = {}


def validate_chords(chords: list[str]) -> list[str]:
    known = {chord.id.lower(): chord.id for chord in _all_chords}
    normalized: list[str] = []
    for chord in chords:
        match = known.get(chord.lower())
        if not match:
            raise HTTPException(status_code=400, detail=f"Unknown chord: {chord}")
        normalized.append(match)
    return normalized


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@router.get("/progressions", response_model=ProgressionListResponse)
async def list_progressions():
    progressions = list(_progressions.values())
    return {"progressions": progressions, "total": len(progressions)}


@router.post(
    "/progressions",
    response_model=ProgressionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_progression(request: ProgressionCreateRequest):
    timestamp = now_iso()
    progression_id = str(uuid4())
    progression = {
        "id": progression_id,
        "name": request.name,
        "chords": validate_chords(request.chords),
        "tonality": request.tonality,
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }
    _progressions[progression_id] = progression
    return progression


@router.get("/progressions/{progression_id}", response_model=ProgressionResponse)
async def get_progression(progression_id: str):
    progression = _progressions.get(progression_id)
    if not progression:
        raise HTTPException(status_code=404, detail="Progression not found")
    return progression


@router.put("/progressions/{progression_id}", response_model=ProgressionResponse)
async def update_progression(
    progression_id: str,
    request: ProgressionUpdateRequest,
):
    progression = _progressions.get(progression_id)
    if not progression:
        raise HTTPException(status_code=404, detail="Progression not found")
    if request.name is not None:
        progression["name"] = request.name
    if request.chords is not None:
        progression["chords"] = validate_chords(request.chords)
    if request.tonality is not None:
        progression["tonality"] = request.tonality
    progression["updatedAt"] = now_iso()
    return progression


@router.delete("/progressions/{progression_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_progression(progression_id: str):
    if progression_id not in _progressions:
        raise HTTPException(status_code=404, detail="Progression not found")
    del _progressions[progression_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
