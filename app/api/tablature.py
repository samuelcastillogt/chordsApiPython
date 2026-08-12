from fastapi import APIRouter, HTTPException

from app.api.schemas import TablatureRequest, TablatureResponse
from app.domain.chord import ChordNode, NOTES, Note

router = APIRouter()
_all_chords = ChordNode.build_all()
_known_chords = {chord.id.lower(): chord for chord in _all_chords}

TUNING = ["e", "B", "G", "D", "A", "E"]
STRING_NOTES = [Note.E, Note.B, Note.G, Note.D, Note.A, Note.E]

COMMON_SHAPES: dict[str, list[str]] = {
    "C": ["0", "1", "0", "2", "3", "x"],
    "Cm": ["3", "4", "5", "5", "3", "x"],
    "C7": ["0", "1", "3", "2", "3", "x"],
    "D": ["2", "3", "2", "0", "x", "x"],
    "Dm": ["1", "3", "2", "0", "x", "x"],
    "D7": ["2", "1", "2", "0", "x", "x"],
    "E": ["0", "0", "1", "2", "2", "0"],
    "Em": ["0", "0", "0", "2", "2", "0"],
    "E7": ["0", "0", "1", "0", "2", "0"],
    "F": ["1", "1", "2", "3", "3", "1"],
    "Fm": ["1", "1", "1", "3", "3", "1"],
    "F7": ["1", "1", "2", "1", "3", "1"],
    "G": ["3", "0", "0", "0", "2", "3"],
    "Gm": ["3", "3", "3", "5", "5", "3"],
    "G7": ["1", "0", "0", "0", "2", "3"],
    "A": ["0", "2", "2", "2", "0", "x"],
    "Am": ["0", "1", "2", "2", "0", "x"],
    "A7": ["0", "2", "0", "2", "0", "x"],
    "B": ["2", "4", "4", "4", "2", "x"],
    "Bm": ["2", "3", "4", "4", "2", "x"],
    "B7": ["2", "0", "2", "1", "2", "x"],
}


def note_index(note: Note) -> int:
    return NOTES.index(note)


def normalize_chords(chords: list[str]) -> list[ChordNode]:
    normalized: list[ChordNode] = []
    for chord in chords:
        match = _known_chords.get(chord.lower())
        if not match:
            raise HTTPException(status_code=400, detail=f"Unknown chord: {chord}")
        normalized.append(match)
    return normalized


def fret_for_note(open_note: Note, target: Note, max_fret: int = 7) -> str | None:
    distance = (note_index(target) - note_index(open_note)) % 12
    if distance <= max_fret:
        return str(distance)
    return None


def fallback_shape(chord: ChordNode) -> list[str]:
    frets = ["x", "x", "x", "x", "x", "x"]
    used_notes: set[Note] = set()
    for string_index, open_note in enumerate(STRING_NOTES[:4]):
        options = [note for note in chord.triad if note not in used_notes] or list(chord.triad)
        best = min(
            ((fret_for_note(open_note, note), note) for note in options),
            key=lambda item: int(item[0]) if item[0] is not None else 99,
        )
        if best[0] is not None:
            frets[string_index] = best[0]
            used_notes.add(best[1])
    return frets


def chord_shape(chord: ChordNode) -> list[str]:
    return COMMON_SHAPES.get(chord.id, fallback_shape(chord))


def build_tablature(chords: list[ChordNode]) -> tuple[list[str], list[dict[str, list[str]]]]:
    diagrams = [{"chord": chord.id, "frets": chord_shape(chord)} for chord in chords]
    lines: list[str] = []
    for string_index, string_name in enumerate(TUNING):
        parts = [diagram["frets"][string_index].center(max(3, len(diagram["chord"])), "-") for diagram in diagrams]
        lines.append(f"{string_name}|" + "-".join(parts) + "|")
    return lines, diagrams


def build_arpeggio(diagrams: list[dict[str, list[str]]]) -> list[str]:
    pattern = [5, 4, 3, 2, 1, 0, 1, 2]
    lines = [f"{string_name}|" for string_name in TUNING]
    for diagram in diagrams:
        for string_index in range(len(TUNING)):
            lines[string_index] += "--"
        for step in pattern:
            fret = diagram["frets"][step]
            played = fret if fret != "x" else "-"
            cell_width = max(2, len(played))
            for string_index in range(len(TUNING)):
                cell = played if string_index == step else "-"
                lines[string_index] += cell.center(cell_width, "-")
        for string_index in range(len(TUNING)):
            lines[string_index] += "-"
    return [f"{line}|" for line in lines]


@router.post("/tablature", response_model=TablatureResponse)
async def generate_tablature(request: TablatureRequest):
    chords = normalize_chords(request.chords)
    title = request.title.strip() if request.title else "ChordWeaver tablatura"
    lines, diagrams = build_tablature(chords)
    arpeggio_lines = build_arpeggio(diagrams)
    header = [title, f"Acordes: {' - '.join(chord.id for chord in chords)}", "Afinacion: E A D G B e"]
    text = "\n".join([*header, "", "Rasgueo / posiciones:", *lines, "", "Arpegio sugerido (solo cuerda y traste):", *arpeggio_lines])
    return {
        "title": title,
        "tuning": TUNING,
        "chords": [chord.id for chord in chords],
        "lines": lines,
        "arpeggioLines": arpeggio_lines,
        "text": text,
        "diagrams": diagrams,
    }
