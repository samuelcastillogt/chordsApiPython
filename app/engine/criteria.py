from app.domain.chord import ChordNode, ChordType, CIRCLE_OF_FIFTHS

NOTES_ORDER = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
]


def note_index(note) -> int:
    return NOTES_ORDER.index(note.value if hasattr(note, "value") else note)


def shared_notes(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    common = len(set(a.triad) & set(b.triad))
    scores = {3: 100.0, 2: 80.0, 1: 40.0, 0: 0.0}
    return scores[common], f"{common} nota(s) en común: {set(a.triad) & set(b.triad)}"


def circle_distance(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    d = abs(a.circle_position - b.circle_position)
    d = min(d, 12 - d)
    scores = {1: 90.0, 2: 70.0, 3: 50.0, 4: 30.0, 5: 30.0, 6: 10.0}
    return scores.get(d, 0.0), f"Distancia {d} pasos en círculo de quintas"


def voice_movement(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    import itertools
    best_total_semitones = 999
    for perm in itertools.permutations(range(3)):
        total = 0
        for i, j in enumerate(perm):
            ai = note_index(a.triad[i])
            bi = note_index(b.triad[j])
            d = min(abs(ai - bi), 12 - abs(ai - bi))
            total += d
        best_total_semitones = min(best_total_semitones, total)
    scores = {0: 100, 1: 80, 2: 60, 3: 40, 4: 20}
    raw = scores.get(best_total_semitones, 10)
    return float(raw), f"Movimiento voces: {best_total_semitones} semitonos totales"


def transformation_type(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    if a.root == b.root and a.chord_type == ChordType.MAJOR and b.chord_type == ChordType.MINOR:
        return 90.0, "Paralelo mayor→menor"
    if a.root == b.root and a.chord_type == ChordType.MAJOR and b.chord_type == ChordType.DOM7:
        return 80.0, "Mayor→dominante"
    if a.root == b.root and a.chord_type == ChordType.MAJOR and b.chord_type == ChordType.AUG:
        return 60.0, "Mayor→aumentado"
    if a.root == b.root and a.chord_type == ChordType.MINOR and b.chord_type == ChordType.DIM:
        return 60.0, "Menor→disminuido"
    if a.chord_type == ChordType.DOM7 and b.chord_type == ChordType.DOM7:
        a_pos = (a.circle_position + 6) % 12
        if b.circle_position == a_pos:
            return 50.0, "Sustituto tritonal"
    return 20.0, "Otra transformación"


def tonal_function(a: ChordNode, b: ChordNode, tonality: str | None = None) -> tuple[float, str]:
    if not tonality:
        return 50.0, "Sin tonalidad de referencia"
    return 50.0, "Función tonal base"


def dominant_chain(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    if a.chord_type == ChordType.DOM7:
        target_pos = (a.circle_position - 1) % 12
        target_root = CIRCLE_OF_FIFTHS[target_pos]
        if b.root == target_root and b.chord_type in (ChordType.MAJOR, ChordType.MINOR):
            return 100.0, f"Dominante natural: {a.id} → {b.id}"
    return 0.0, "No es cadena de dominantes"


def glue_magic(a: ChordNode, b: ChordNode) -> tuple[float, str]:
    common = set(a.triad) & set(b.triad)
    if not common:
        return 0.0, "Sin notas puente"
    bonus = 0
    note = a.root if a.root in common else sorted(common, key=note_index)[0]
    if note == a.root:
        bonus += 30
    return float(bonus), f"Nota puente: {note.value if hasattr(note, 'value') else note}"
