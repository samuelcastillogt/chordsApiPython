from fastapi import APIRouter

from app.api.schemas import ChordResponse, ParseRequest, ParseResponse
from app.domain.catalog import ALL_CHORDS, find_chord, parse
from app.domain.chord import QUALITIES, ChordNode, ChordParseError

router = APIRouter()


def serialize_chord(chord: ChordNode) -> dict:
    return {
        "id": chord.id,
        "root": chord.root.value,
        "type": chord.chord_type.value,
        "family": chord.family,
        "label": QUALITIES[chord.chord_type].label,
        "notes": [note.value for note in chord.notes],
        "triad": [note.value for note in chord.triad],
        "circlePosition": chord.circle_position,
    }


@router.get("/chords", response_model=list[ChordResponse])
async def list_chords():
    return [serialize_chord(chord) for chord in ALL_CHORDS]


@router.post("/chords/parse", response_model=ParseResponse)
async def parse_chords(request: ParseRequest):
    """Normalises free-form chord symbols (American or Latin, flats, slash chords)."""
    results = []
    for symbol in request.symbols:
        try:
            parsed = parse(symbol)
            results.append({
                "input": symbol,
                "chord": parsed.chord.id,
                "bass": parsed.bass.value if parsed.bass else None,
                "approximated": parsed.approximated,
            })
        except ChordParseError as error:
            results.append({"input": symbol, "chord": None, "error": str(error)})
    return {"results": results}


@router.get("/chords/{chord_id}", response_model=ChordResponse)
async def get_chord(chord_id: str):
    return serialize_chord(find_chord(chord_id, status_code=404))
