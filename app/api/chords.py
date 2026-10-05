from fastapi import APIRouter, HTTPException

from app.api.schemas import ChordResponse
from app.domain.chord import ChordNode

router = APIRouter()

_all_chords = ChordNode.build_all()


def serialize_chord(chord: ChordNode) -> dict:
    return {
        "id": chord.id,
        "root": chord.root.value,
        "type": chord.chord_type.value,
        "triad": [note.value for note in chord.triad],
        "circlePosition": chord.circle_position,
    }


@router.get("/chords", response_model=list[ChordResponse])
async def list_chords():
    return [serialize_chord(chord) for chord in _all_chords]


@router.get("/chords/{chord_id}", response_model=ChordResponse)
async def get_chord(chord_id: str):
    for c in _all_chords:
        if c.id.lower() == chord_id.lower():
            return serialize_chord(c)
    raise HTTPException(status_code=404, detail="Chord not found")
