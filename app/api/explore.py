from fastapi import APIRouter, HTTPException

from app.api.schemas import ConnectionsResponse, ExploreRequest, ExploreResponse
from app.domain.catalog import CORE_CHORDS, find_chord
from app.domain.theory import parse_key
from app.engine.connection_engine import find_connections, intent_for

router = APIRouter()


TENSION_CATEGORY = {
    "natural": "natural",
    "medium": "media",
    "media": "media",
    "tense": "tensa",
    "tensa": "tensa",
    "extreme": "extrema",
    "extrema": "extrema",
}


def serialize_connection(connection) -> dict:
    explanation = next((criterion.details for criterion in connection.breakdown if criterion.name == "transformation"), "")
    return {
        "source": connection.source.id,
        "target": connection.target.id,
        "score": connection.total,
        "intent": intent_for(connection.total),
        "category": connection.category,
        "explanation": explanation + f" · conexión {connection.category} ({connection.total}).",
        "breakdown": {
            item.name: {
                "raw": item.raw_score,
                "weighted": round(item.weighted_score, 1),
                "detail": item.details,
            }
            for item in connection.breakdown
        },
    }


def validate_tonality(tonality: str | None) -> str | None:
    if tonality is None:
        return None
    key = parse_key(tonality)
    if key is None:
        raise HTTPException(status_code=400, detail=f"Unknown tonality: {tonality}")
    return key.id


@router.get("/chords/{chord_id}/connections", response_model=ConnectionsResponse)
async def get_connections(
    chord_id: str,
    tonality: str | None = None,
    min_score: float = 0,
    max_results: int = 12,
):
    current = find_chord(chord_id, status_code=404)
    connections = find_connections(current, CORE_CHORDS, validate_tonality(tonality), min_score, max(1, min(max_results, 72)))
    return {
        "contractVersion": "1",
        "source": current.id,
        "connections": [serialize_connection(connection) for connection in connections],
        "total": len(connections),
    }


@router.post("/explore", response_model=ExploreResponse)
async def explore_next_chords(request: ExploreRequest):
    current = find_chord(request.currentChord, status_code=404)
    connections = find_connections(
        current,
        CORE_CHORDS,
        tonality=validate_tonality(request.tonality),
        max_results=len(CORE_CHORDS),
    )
    if request.preferredTension:
        category = TENSION_CATEGORY[request.preferredTension]
        connections = [item for item in connections if item.category == category]
    connections = connections[: request.maxResults]
    return {
        "contractVersion": "1",
        "currentChord": current.id,
        "suggestions": [
            {
                **serialize_connection(item),
                "chord": item.target.id,
            }
            for item in connections
        ],
        "total": len(connections),
    }
