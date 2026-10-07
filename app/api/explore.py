from fastapi import APIRouter

from app.api.schemas import ConnectionsResponse, ExploreRequest, ExploreResponse
from app.domain.catalog import CORE_CHORDS, find_chord
from app.engine.connection_engine import find_connections

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
    return {
        "target": connection.target.id,
        "score": connection.total,
        "category": connection.category,
        "breakdown": {
            item.name: {
                "raw": item.raw_score,
                "weighted": round(item.weighted_score, 1),
                "detail": item.details,
            }
            for item in connection.breakdown
        },
    }


@router.get("/chords/{chord_id}/connections", response_model=ConnectionsResponse)
async def get_connections(
    chord_id: str,
    tonality: str | None = None,
    min_score: float = 0,
    max_results: int = 12,
):
    current = find_chord(chord_id, status_code=404)
    connections = find_connections(current, CORE_CHORDS, tonality, min_score, max(1, min(max_results, 72)))
    return {
        "source": current.id,
        "connections": [serialize_connection(connection) for connection in connections],
        "total": len(connections),
    }


@router.post("/explore", response_model=ExploreResponse)
async def explore_next_chords(request: ExploreRequest):
    current = find_chord(request.currentChord, status_code=404)
    connections = find_connections(current, CORE_CHORDS, tonality=request.tonality, max_results=len(CORE_CHORDS))
    if request.preferredTension:
        category = TENSION_CATEGORY[request.preferredTension]
        connections = [item for item in connections if item.category == category]
    connections = connections[: request.maxResults]
    return {
        "currentChord": current.id,
        "suggestions": [
            {
                "chord": item.target.id,
                "score": item.total,
                "category": item.category,
                "explanation": next(
                    (criterion.details for criterion in item.breakdown if criterion.name == "transformation"),
                    "",
                )
                + f" · conexión {item.category} ({item.total}).",
            }
            for item in connections
        ],
        "total": len(connections),
    }
