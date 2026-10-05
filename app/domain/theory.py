"""Tonal analysis: keys, roman numerals, harmonic functions and substitutions."""

from dataclasses import dataclass

from app.domain.chord import (
    NOTE_INDEX,
    NOTES,
    ChordNode,
    ChordType,
    FLAT_NAMES,
    Note,
    QUALITIES,
    _parse_root,
)

MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
NATURAL_MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)

DEGREE_NAMES = {
    "major": {0: "I", 1: "bII", 2: "II", 3: "bIII", 4: "III", 5: "IV", 6: "#IV", 7: "V", 8: "bVI", 9: "VI", 10: "bVII", 11: "VII"},
    "minor": {0: "I", 1: "bII", 2: "II", 3: "III", 4: "#III", 5: "IV", 6: "#IV", 7: "V", 8: "VI", 9: "#VI", 10: "VII", 11: "#VII"},
}

FUNCTIONS = {
    "major": {0: "T", 4: "T", 9: "T", 2: "SD", 5: "SD", 7: "D", 11: "D"},
    "minor": {0: "T", 3: "T", 8: "T", 2: "SD", 5: "SD", 7: "D", 10: "D", 11: "D"},
}

SPANISH_NAMES = ["Do", "Do#", "Re", "Mib", "Mi", "Fa", "Fa#", "Sol", "Lab", "La", "Sib", "Si"]

FUNCTION_LABELS = {"T": "tónica", "SD": "subdominante", "D": "dominante"}

NUMERAL_SUFFIX = {
    ChordType.MAJOR: "", ChordType.MINOR: "", ChordType.DIM: "°", ChordType.AUG: "+",
    ChordType.DOM7: "7", ChordType.DIM7: "°7", ChordType.MAJ7: "maj7", ChordType.MIN7: "7",
    ChordType.HALF_DIM7: "ø7", ChordType.SUS2: "sus2", ChordType.SUS4: "sus4", ChordType.ADD9: "add9",
    ChordType.SIX: "6", ChordType.MIN6: "6", ChordType.DOM9: "9", ChordType.POWER: "5",
}


@dataclass(frozen=True)
class Key:
    tonic: Note
    mode: str  # "major" | "minor"

    @property
    def id(self) -> str:
        return f"{self.tonic.value}{'m' if self.mode == 'minor' else ''}"

    @property
    def label(self) -> str:
        """Spanish name plus the chord symbol, e.g. "Si menor (Bm)"."""
        index = NOTE_INDEX[self.tonic]
        symbol = (FLAT_NAMES[index] if self.tonic.value in ("A#", "D#") else self.tonic.value) + ("m" if self.mode == "minor" else "")
        return f"{SPANISH_NAMES[index]} {'menor' if self.mode == 'minor' else 'mayor'} ({symbol})"

    @property
    def scale(self) -> frozenset[int]:
        steps = MAJOR_SCALE if self.mode == "major" else NATURAL_MINOR_SCALE
        return frozenset((NOTE_INDEX[self.tonic] + step) % 12 for step in steps)

    def degree(self, note: Note) -> int:
        return (NOTE_INDEX[note] - NOTE_INDEX[self.tonic]) % 12


ALL_KEYS = [Key(note, mode) for mode in ("major", "minor") for note in NOTES]


def parse_key(value: str | None) -> Key | None:
    if not value:
        return None
    text = value.strip()
    parsed = _parse_root(text)
    if not parsed:
        return None
    tonic, rest = parsed
    rest = rest.strip().lower()
    if rest in ("", "maj", "major", "mayor"):
        return Key(tonic, "major")
    if rest in ("m", "min", "minor", "menor", "-"):
        return Key(tonic, "minor")
    return None


def is_diatonic(chord: ChordNode, key: Key) -> bool:
    if chord.pitch_classes <= key.scale:
        return True
    if key.mode == "minor":
        # Harmonic minor: V, V7 and vii°7 are idiomatic.
        degree = key.degree(chord.root)
        if degree == 7 and chord.chord_type in (ChordType.MAJOR, ChordType.DOM7, ChordType.DOM9):
            return True
        if degree == 11 and chord.chord_type in (ChordType.DIM, ChordType.DIM7):
            return True
    return False


def _numeral(chord: ChordNode, key: Key) -> str:
    degree = key.degree(chord.root)
    numeral = DEGREE_NAMES[key.mode][degree]
    if chord.family in ("minor", "diminished"):
        numeral = numeral[:-len(numeral.lstrip("b#"))] + numeral.lstrip("b#").lower()
    return numeral + NUMERAL_SUFFIX[chord.chord_type]


def _diatonic_root_numeral(root_index: int, key: Key) -> str | None:
    """Numeral of the diatonic triad built on a scale degree (for V/x labels)."""
    degree = (root_index - NOTE_INDEX[key.tonic]) % 12
    steps = MAJOR_SCALE if key.mode == "major" else NATURAL_MINOR_SCALE
    if degree not in steps:
        return None
    scale = key.scale
    third = (root_index + 3) % 12 in scale and (root_index + 4) % 12 not in scale
    fifth_dim = (root_index + 6) % 12 in scale and (root_index + 7) % 12 not in scale
    numeral = DEGREE_NAMES[key.mode][degree]
    if third:
        numeral = numeral.lower() + ("°" if fifth_dim else "")
    return numeral


@dataclass(frozen=True)
class ChordAnalysis:
    chord: ChordNode
    numeral: str
    function: str | None
    role: str  # diatonic | secondary_dominant | borrowed | chromatic
    explanation: str


def analyze_chord(chord: ChordNode, key: Key) -> ChordAnalysis:
    degree = key.degree(chord.root)
    numeral = _numeral(chord, key)

    if is_diatonic(chord, key):
        function = FUNCTIONS[key.mode].get(degree)
        label = FUNCTION_LABELS.get(function or "", "color")
        return ChordAnalysis(chord, numeral, function, "diatonic", f"{numeral}: acorde de la tonalidad con función de {label}.")

    if chord.family in ("dominant", "major") and chord.chord_type not in (ChordType.MAJ7, ChordType.ADD9, ChordType.SIX):
        target_index = (NOTE_INDEX[chord.root] + 5) % 12
        target = _diatonic_root_numeral(target_index, key)
        if target and target not in ("I", "i"):
            secondary = f"V{'7' if chord.family == 'dominant' else ''}/{target}"
            return ChordAnalysis(
                chord, secondary, "D", "secondary_dominant",
                f"{secondary}: dominante secundaria, crea tensión que resuelve en {target}.",
            )

    parallel = Key(key.tonic, "minor" if key.mode == "major" else "major")
    if is_diatonic(chord, parallel):
        function = FUNCTIONS[parallel.mode].get(degree)
        return ChordAnalysis(
            chord, numeral, function, "borrowed",
            f"{numeral}: acorde prestado de {parallel.label}; aporta un color {'oscuro' if parallel.mode == 'minor' else 'luminoso'}.",
        )

    return ChordAnalysis(chord, numeral, None, "chromatic", f"{numeral}: acorde cromático, fuera de la tonalidad.")


@dataclass(frozen=True)
class KeyGuess:
    key: Key
    score: float
    confidence: float


def detect_key(chords: list[ChordNode]) -> KeyGuess:
    if not chords:
        raise ValueError("At least one chord is required")

    weights = {"diatonic": 1.0, "secondary_dominant": 0.55, "borrowed": 0.3, "chromatic": 0.0}
    ranked: list[tuple[float, Key]] = []
    for key in ALL_KEYS:
        score = sum(weights[analyze_chord(chord, key).role] for chord in chords) / len(chords)
        tonic_type = ChordType.MAJOR if key.mode == "major" else ChordType.MINOR
        tonic_like = {tonic_type, ChordType.MAJ7 if key.mode == "major" else ChordType.MIN7, ChordType.SIX if key.mode == "major" else ChordType.MIN6, ChordType.ADD9 if key.mode == "major" else ChordType.MINOR, ChordType.POWER}
        if chords[0].root == key.tonic and chords[0].chord_type in tonic_like:
            score += 0.15
        if chords[-1].root == key.tonic and chords[-1].chord_type in tonic_like:
            score += 0.2
        dominant_count = sum(1 for chord in chords if chord.family == "dominant")
        blues_degrees = {key.degree(chord.root) for chord in chords} <= {0, 5, 7}
        if key.mode == "major" and dominant_count >= 3 and blues_degrees and chords[0].root == key.tonic:
            score += 0.5  # Blues: I7, IV7 and V7 are all dominant chords.
        for previous, current in zip(chords, chords[1:]):
            if key.degree(previous.root) == 7 and previous.family in ("major", "dominant") and current.root == key.tonic:
                score += 0.1
                break
        ranked.append((score, key))

    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best_key = ranked[0]
    runner_up = ranked[1][0] if len(ranked) > 1 else 0
    confidence = 1.0 if best_score <= 0 else min(1.0, 0.5 + (best_score - runner_up) / max(best_score, 0.01))
    return KeyGuess(best_key, round(best_score, 3), round(confidence, 2))


@dataclass(frozen=True)
class Substitution:
    chord: str
    kind: str
    reason: str


def suggest_substitutions(chord: ChordNode, key: Key, catalog: dict[str, ChordNode]) -> list[Substitution]:
    def chord_id(root_offset: int, chord_type: ChordType) -> str | None:
        root = NOTES[(NOTE_INDEX[chord.root] + root_offset) % 12]
        candidate = f"{root.value}{QUALITIES[chord_type].suffix}"
        return candidate if candidate in catalog else None

    suggestions: list[Substitution] = []

    def add(candidate: str | None, kind: str, reason: str) -> None:
        if candidate and candidate != chord.id and all(item.chord != candidate for item in suggestions):
            suggestions.append(Substitution(candidate, kind, reason))

    if chord.family == "major":
        add(chord_id(9, ChordType.MINOR), "relativo", "Relativo menor: comparte dos notas y suaviza el movimiento.")
        add(chord_id(0, ChordType.MAJ7), "color", "Añade la séptima mayor para un sonido más abierto.")
        add(chord_id(0, ChordType.ADD9), "color", "La novena agregada da brillo sin cambiar la función.")
    if chord.family == "minor":
        add(chord_id(3, ChordType.MAJOR), "relativo", "Relativo mayor: misma familia de notas, más luminoso.")
        add(chord_id(0, ChordType.MIN7), "color", "La séptima menor lo hace más suave y jazzero.")
    if chord.family == "dominant":
        add(chord_id(6, ChordType.DOM7), "tritono", "Sustituto tritonal: misma tensión, bajo cromático hacia la resolución.")
        add(chord_id(0, ChordType.SUS4), "suspensión", "Suspende la tercera y retrasa la resolución.")

    degree = key.degree(chord.root)
    if key.mode == "major" and degree == 5 and chord.family == "major":
        add(chord_id(0, ChordType.MINOR), "préstamo", "iv prestado del modo menor: el clásico giro melancólico.")
    if key.mode == "major" and degree == 7 and chord.family in ("major", "dominant"):
        add(chord_id(3, ChordType.MAJOR), "préstamo", "bVII prestado: cadencia rockera hacia la tónica.")

    add(chord_id(7, ChordType.DOM7), "preparación", f"Antes de {chord.id}, toca su dominante para crear expectativa.")
    return suggestions[:4]
