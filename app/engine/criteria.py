import itertools

from app.domain.chord import CIRCLE_OF_FIFTHS, NOTE_INDEX, ChordNode, ChordType
from app.domain.theory import FUNCTIONS, analyze_chord, parse_key


def note_index(note) -> int:
    return NOTE_INDEX[note]


def shared_notes(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    common = a.pitch_classes & b.pitch_classes
    ratio = len(common) / min(len(a.pitch_classes), len(b.pitch_classes))
    score = 100.0 if ratio >= 1 else 85.0 if ratio >= 0.66 else 70.0 if ratio >= 0.5 else 55.0 if ratio >= 0.33 else 40.0 if ratio > 0 else 0.0
    names = sorted(note.value for note in set(a.notes) & set(b.notes))
    return score, f"{len(common)} nota(s) en común: {', '.join(names) or 'ninguna'}"


def circle_distance(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    d = abs(a.circle_position - b.circle_position)
    d = min(d, 12 - d)
    scores = {0: 80.0, 1: 90.0, 2: 70.0, 3: 50.0, 4: 30.0, 5: 30.0, 6: 10.0}
    return scores.get(d, 0.0), f"Distancia {d} pasos en círculo de quintas"


def voice_movement(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    """Smallest total semitone motion when moving the voices of a into b."""
    small, large = (a.notes, b.notes) if len(a.notes) <= len(b.notes) else (b.notes, a.notes)
    best = min(
        sum(
            min(abs(note_index(x) - note_index(y)), 12 - abs(note_index(x) - note_index(y)))
            for x, y in zip(small, perm)
        )
        for perm in itertools.permutations(large, len(small))
    )
    scores = {0: 100, 1: 90, 2: 80, 3: 65, 4: 50, 5: 35, 6: 20}
    return float(scores.get(best, 10)), f"Movimiento voces: {best} semitonos totales"


def transformation_type(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    interval = (note_index(b.root) - note_index(a.root)) % 12
    if a.root == b.root:
        if a.family == "major" and b.family == "minor":
            return 90.0, "Paralelo mayor→menor"
        if a.family == "minor" and b.family == "major":
            return 85.0, "Paralelo menor→mayor"
        if a.chord_type == ChordType.MAJOR and b.chord_type == ChordType.DOM7:
            return 80.0, "Mayor→dominante"
        if a.family == "suspended" and b.family in ("major", "minor", "dominant"):
            return 85.0, "Resolución de la suspensión"
        if a.family == b.family:
            return 75.0, "Mismo acorde con otro color"
        if a.chord_type == ChordType.MAJOR and b.chord_type == ChordType.AUG:
            return 60.0, "Mayor→aumentado"
        if a.chord_type == ChordType.MINOR and b.chord_type == ChordType.DIM:
            return 60.0, "Menor→disminuido"
    if a.family == "major" and b.family == "minor" and interval == 9:
        return 85.0, "Relativo menor"
    if a.family == "minor" and b.family == "major" and interval == 3:
        return 85.0, "Relativo mayor"
    if a.family == "dominant" and b.family == "dominant" and interval == 6:
        return 50.0, "Sustituto tritonal"
    if a.family == "dominant" and interval == 5 and b.family in ("major", "minor"):
        return 95.0, "Resolución dominante → tónica"
    if interval == 5:
        return 75.0, "Movimiento de cuarta (plagal)"
    if interval == 7:
        return 70.0, "Movimiento de quinta (hacia la dominante)"
    if interval in (2, 10) and a.family == b.family:
        return 55.0, "Paso por grado conjunto"
    return 20.0, "Otra transformación"


FUNCTION_FLOW = {
    ("T", "SD"): 80.0, ("T", "D"): 70.0, ("T", "T"): 60.0,
    ("SD", "D"): 95.0, ("SD", "T"): 75.0, ("SD", "SD"): 55.0,
    ("D", "T"): 100.0, ("D", "D"): 45.0, ("D", "SD"): 35.0,
}


def tonal_function(a: ChordNode, b: ChordNode, tonality: str | None = None) -> tuple[float, str]:
    key = parse_key(tonality)
    if not key:
        return 50.0, "Sin tonalidad de referencia"
    source = analyze_chord(a, key)
    target = analyze_chord(b, key)
    if target.role == "chromatic":
        return 15.0, f"{b.id} está fuera de {key.label}"
    if target.role == "borrowed":
        return 45.0, f"{b.id} es un acorde prestado ({target.numeral})"
    if source.function and target.function:
        score = FUNCTION_FLOW.get((source.function, target.function), 50.0)
        if target.role == "secondary_dominant":
            score = min(score, 70.0)
        return score, f"{source.numeral} → {target.numeral} ({source.function}→{target.function}) en {key.label}"
    return 50.0, f"{target.numeral} en {key.label}"


def dominant_chain(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    if a.family == "dominant" or a.chord_type == ChordType.MAJOR:
        target_root = CIRCLE_OF_FIFTHS[(a.circle_position - 1) % 12]
        if b.root == target_root and b.family in ("major", "minor", "dominant"):
            score = 100.0 if a.family == "dominant" else 60.0
            return score, f"Resolución por quinta: {a.id} → {b.id}"
    return 0.0, "No es cadena de dominantes"


def glue_magic(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    common = set(a.notes) & set(b.notes)
    if not common:
        return 0.0, "Sin notas puente"
    note = a.root if a.root in common else sorted(common, key=note_index)[0]
    bonus = 30.0 if note == a.root else 0.0
    return bonus, f"Nota puente: {note.value}"


__all__ = [
    "FUNCTIONS",
    "circle_distance",
    "dominant_chain",
    "glue_magic",
    "shared_notes",
    "tonal_function",
    "transformation_type",
    "voice_movement",
]
