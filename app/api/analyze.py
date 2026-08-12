from fastapi import APIRouter, HTTPException

from app.api.explore import serialize_connection
from app.api.schemas import AnalyzeRequest, AnalyzeResponse
from app.domain.chord import ChordNode
from app.engine.connection_engine import find_connections

router = APIRouter()
_all_chords = ChordNode.build_all()


def chord_by_id(chord_id: str) -> ChordNode:
    chord = next((item for item in _all_chords if item.id.lower() == chord_id.lower()), None)
    if not chord:
        raise HTTPException(status_code=400, detail=f"Unknown chord: {chord_id}")
    return chord


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_progression(request: AnalyzeRequest):
    chords = [chord_by_id(chord_id) for chord_id in request.chords]
    connections = []
    tension_curve = []

    for index, source in enumerate(chords[:-1]):
        target = chords[index + 1]
        matches = find_connections(
            source,
            _all_chords,
            tonality=request.tonality,
            min_score=0,
            max_results=len(_all_chords),
        )
        connection = next(item for item in matches if item.target.id == target.id)
        serialized = serialize_connection(connection)
        connections.append({"source": source.id, **serialized})
        tension_curve.append(
            {
                "from": source.id,
                "to": target.id,
                "score": connection.total,
                "category": connection.category,
            }
        )

    average_score = round(
        sum(item["score"] for item in tension_curve) / len(tension_curve),
        1,
    )
    suggestions = []
    if average_score < 50:
        suggestions.append("La progresión tiene alta tensión; prueba insertar acordes puente.")
    else:
        suggestions.append("La progresión mantiene continuidad armónica estable.")

    return {
        "analysis": {
            "chords": [chord.id for chord in chords],
            "connections": connections,
            "tensionCurve": tension_curve,
            "averageScore": average_score,
            "suggestions": suggestions,
        }
    }
