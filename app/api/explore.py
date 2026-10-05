from fastapi import APIRouter, HTTPException

from app.api.schemas import ConnectionsResponse, ExploreRequest, ExploreResponse
from app.domain.chord import ChordNode
from app.engine.connection_engine import find_connections

router = APIRouter()
_all_chords = ChordNode.build_all()


TENSION_CATEGORY = {
    "natural": "natural",
    "medium": "media",
    "media": "media",
    "tense": "tensa",
    "tensa": "tensa",
    "extreme": "extrema",
    "extrema": "extrema",
}


def get_chord_or_404(chord_id: str) -> ChordNode:
    current = next((c for c in _all_chords if c.id.lower() == chord_id.lower()), None)
    if not current:
        raise HTTPException(status_code=404, detail="Chord not found")
    return current


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
    current = get_chord_or_404(chord_id)

    connections = find_connections(current, _all_chords, tonality, min_score, max_results)
    return {
        "source": current.id,
        "connections": [serialize_connection(connection) for connection in connections],
        "total": len(connections),
    }


@router.post("/explore", response_model=ExploreResponse)
async def explore_next_chords(request: ExploreRequest):
    current = get_chord_or_404(request.currentChord)
    connections = find_connections(
        current,
        _all_chords,
        tonality=request.tonality,
        min_score=0,
        max_results=len(_all_chords),
    )
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
                "explanation": (
                    f"{item.target.id} es una conexión {item.category} desde "
                    f"{current.id} con score {item.total}."
                ),
            }
            for item in connections
        ],
        "total": len(connections),
    }
