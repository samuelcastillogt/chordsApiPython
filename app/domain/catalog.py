from fastapi import HTTPException

from app.domain.chord import CORE_TYPES, ChordNode, ChordParseError, ParsedChord, parse_chord_symbol

ALL_CHORDS: list[ChordNode] = ChordNode.build_all()
BY_ID: dict[str, ChordNode] = {chord.id: chord for chord in ALL_CHORDS}
CORE_CHORDS: list[ChordNode] = [chord for chord in ALL_CHORDS if chord.chord_type in CORE_TYPES]


def parse(symbol: str) -> ParsedChord:
    exact = BY_ID.get(symbol)
    if exact:
        return ParsedChord(symbol, exact, None, False)
    return parse_chord_symbol(symbol, BY_ID)


def find_chord(symbol: str, status_code: int = 400) -> ChordNode:
    """Resolves any chord symbol to a catalog chord or raises an HTTP error."""
    try:
        return parse(symbol).chord
    except ChordParseError as error:
        detail = "Chord not found" if status_code == 404 else str(error)
        raise HTTPException(status_code=status_code, detail=detail) from error
