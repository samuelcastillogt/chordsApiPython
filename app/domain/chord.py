import re
from dataclasses import dataclass
from enum import Enum


class Note(str, Enum):
    C = "C"
    CSHARP = "C#"
    D = "D"
    DSHARP = "D#"
    E = "E"
    F = "F"
    FSHARP = "F#"
    G = "G"
    GSHARP = "G#"
    A = "A"
    ASHARP = "A#"
    B = "B"


class ChordType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    DIM = "dim"
    AUG = "aug"
    DOM7 = "dom7"
    DIM7 = "dim7"
    MAJ7 = "maj7"
    MIN7 = "m7"
    HALF_DIM7 = "m7b5"
    SUS2 = "sus2"
    SUS4 = "sus4"
    ADD9 = "add9"
    SIX = "6"
    MIN6 = "m6"
    DOM9 = "9"
    POWER = "5"


@dataclass(frozen=True)
class Quality:
    suffix: str
    intervals: tuple[int, ...]
    family: str
    label: str


# Order matters: the first six types keep the original catalog order.
QUALITIES: dict[ChordType, Quality] = {
    ChordType.MAJOR: Quality("", (0, 4, 7), "major", "mayor"),
    ChordType.MINOR: Quality("m", (0, 3, 7), "minor", "menor"),
    ChordType.DIM: Quality("°", (0, 3, 6), "diminished", "disminuido"),
    ChordType.AUG: Quality("+", (0, 4, 8), "augmented", "aumentado"),
    ChordType.DOM7: Quality("7", (0, 4, 7, 10), "dominant", "séptima de dominante"),
    ChordType.DIM7: Quality("°7", (0, 3, 6, 9), "diminished", "séptima disminuida"),
    ChordType.MAJ7: Quality("maj7", (0, 4, 7, 11), "major", "séptima mayor"),
    ChordType.MIN7: Quality("m7", (0, 3, 7, 10), "minor", "menor séptima"),
    ChordType.HALF_DIM7: Quality("m7b5", (0, 3, 6, 10), "diminished", "semidisminuido"),
    ChordType.SUS2: Quality("sus2", (0, 2, 7), "suspended", "suspendido 2"),
    ChordType.SUS4: Quality("sus4", (0, 5, 7), "suspended", "suspendido 4"),
    ChordType.ADD9: Quality("add9", (0, 4, 7, 2), "major", "mayor con novena"),
    ChordType.SIX: Quality("6", (0, 4, 7, 9), "major", "mayor sexta"),
    ChordType.MIN6: Quality("m6", (0, 3, 7, 9), "minor", "menor sexta"),
    ChordType.DOM9: Quality("9", (0, 4, 7, 10, 2), "dominant", "novena de dominante"),
    ChordType.POWER: Quality("5", (0, 7), "power", "quinta (power chord)"),
}

# Chords suggested as "next chord" moves; the rest are colours offered as substitutions.
CORE_TYPES = frozenset({
    ChordType.MAJOR, ChordType.MINOR, ChordType.DOM7, ChordType.MAJ7, ChordType.MIN7,
    ChordType.DIM, ChordType.HALF_DIM7, ChordType.DIM7, ChordType.AUG,
})

NOTES = [Note.C, Note.CSHARP, Note.D, Note.DSHARP, Note.E, Note.F, Note.FSHARP, Note.G, Note.GSHARP, Note.A, Note.ASHARP, Note.B]
NOTE_INDEX = {note: i for i, note in enumerate(NOTES)}
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

CIRCLE_OF_FIFTHS = [Note.C, Note.G, Note.D, Note.A, Note.E, Note.B, Note.FSHARP, Note.DSHARP, Note.ASHARP, Note.F, Note.CSHARP, Note.GSHARP]
CIRCLE_INDEX = {note: i for i, note in enumerate(CIRCLE_OF_FIFTHS)}


def transpose_note(note: Note, semitones: int) -> Note:
    return NOTES[(NOTE_INDEX[note] + semitones) % 12]


def build_chord_notes(root: Note, chord_type: ChordType) -> tuple[Note, ...]:
    return tuple(transpose_note(root, interval) for interval in QUALITIES[chord_type].intervals)


def build_triad(root: Note, chord_type: ChordType) -> tuple[Note, ...]:
    """Kept for backwards compatibility: the first three chord tones."""
    return build_chord_notes(root, chord_type)[:3]


@dataclass(frozen=True)
class ChordNode:
    root: Note
    chord_type: ChordType
    notes: tuple[Note, ...]
    circle_position: int

    @property
    def id(self) -> str:
        return f"{self.root.value}{QUALITIES[self.chord_type].suffix}"

    @property
    def triad(self) -> tuple[Note, ...]:
        return self.notes[:3]

    @property
    def family(self) -> str:
        return QUALITIES[self.chord_type].family

    @property
    def pitch_classes(self) -> frozenset[int]:
        return frozenset(NOTE_INDEX[note] for note in self.notes)

    @classmethod
    def create(cls, root: Note, chord_type: ChordType) -> "ChordNode":
        return cls(
            root=root,
            chord_type=chord_type,
            notes=build_chord_notes(root, chord_type),
            circle_position=CIRCLE_INDEX[root],
        )

    @classmethod
    def build_all(cls) -> list["ChordNode"]:
        return [cls.create(root, chord_type) for root in CIRCLE_OF_FIFTHS for chord_type in QUALITIES]


# --- Chord symbol parsing -------------------------------------------------

ROOT_RE = re.compile(r"^([A-Ga-g])([#b♯♭]?)")
LATIN_ROOT_RE = re.compile(r"^(DO|RE|MI|FA|SOL|LA|SI)([#b♯♭]?)", re.IGNORECASE)
LATIN_TO_AMERICAN = {"DO": "C", "RE": "D", "MI": "E", "FA": "F", "SOL": "G", "LA": "A", "SI": "B"}
NATURAL_INDEX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

EXACT_SUFFIXES: dict[str, ChordType] = {
    "": ChordType.MAJOR, "M": ChordType.MAJOR, "maj": ChordType.MAJOR, "major": ChordType.MAJOR,
    "m": ChordType.MINOR, "min": ChordType.MINOR, "-": ChordType.MINOR, "minor": ChordType.MINOR,
    "dim": ChordType.DIM, "°": ChordType.DIM, "o": ChordType.DIM,
    "aug": ChordType.AUG, "+": ChordType.AUG, "#5": ChordType.AUG,
    "7": ChordType.DOM7, "dom7": ChordType.DOM7,
    "dim7": ChordType.DIM7, "°7": ChordType.DIM7, "o7": ChordType.DIM7,
    "maj7": ChordType.MAJ7, "M7": ChordType.MAJ7, "Δ": ChordType.MAJ7, "Δ7": ChordType.MAJ7, "7M": ChordType.MAJ7, "ma7": ChordType.MAJ7,
    "m7": ChordType.MIN7, "min7": ChordType.MIN7, "-7": ChordType.MIN7,
    "m7b5": ChordType.HALF_DIM7, "ø": ChordType.HALF_DIM7, "ø7": ChordType.HALF_DIM7, "m7-5": ChordType.HALF_DIM7,
    "sus2": ChordType.SUS2, "2": ChordType.SUS2,
    "sus4": ChordType.SUS4, "sus": ChordType.SUS4, "4": ChordType.SUS4,
    "add9": ChordType.ADD9, "add2": ChordType.ADD9,
    "6": ChordType.SIX, "m6": ChordType.MIN6, "min6": ChordType.MIN6,
    "9": ChordType.DOM9, "dom9": ChordType.DOM9,
    "5": ChordType.POWER,
}

# Extended or altered chords mapped to the closest chord the engine knows.
APPROXIMATE_PREFIXES: list[tuple[str, ChordType]] = [
    ("m7b5", ChordType.HALF_DIM7),
    ("mmaj7", ChordType.MINOR),
    ("maj", ChordType.MAJ7),
    ("madd", ChordType.MINOR),
    ("m9", ChordType.MIN7), ("m11", ChordType.MIN7), ("m13", ChordType.MIN7), ("m7", ChordType.MIN7),
    ("m", ChordType.MINOR),
    ("dim", ChordType.DIM7),
    ("7sus", ChordType.DOM7),
    ("sus", ChordType.SUS4),
    ("add", ChordType.ADD9),
    ("6", ChordType.SIX),
    ("11", ChordType.DOM9), ("13", ChordType.DOM9), ("9", ChordType.DOM9),
    ("7", ChordType.DOM7),
    ("aug", ChordType.AUG), ("+", ChordType.AUG),
]


class ChordParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedChord:
    input: str
    chord: ChordNode
    bass: Note | None
    approximated: bool


def _parse_root(text: str) -> tuple[Note, str] | None:
    # Latin names ("DO", "Sol", "SIb") need an uppercase first letter.
    match = LATIN_ROOT_RE.match(text) if text[:1].isupper() else None
    if match:
        letter = LATIN_TO_AMERICAN[match.group(1).upper()]
    else:
        match = ROOT_RE.match(text)
        if not match:
            return None
        letter = match.group(1).upper()
    accidental = match.group(2)
    offset = 1 if accidental in ("#", "♯") else -1 if accidental in ("b", "♭") else 0
    return NOTES[(NATURAL_INDEX[letter] + offset) % 12], text[len(match.group(0)):]


def parse_chord_symbol(symbol: str, catalog: dict[str, ChordNode]) -> ParsedChord:
    """Parses symbols like "Bbmaj7", "F#m7(b5)", "D/F#", "SOLm" or "C9sus4"."""
    text = symbol.strip().replace("(", "").replace(")", "")
    if not text:
        raise ChordParseError("Empty chord symbol")

    root_part = _parse_root(text)
    if not root_part:
        raise ChordParseError(f"Unknown chord: {symbol}")
    root, rest = root_part

    bass: Note | None = None
    if "/" in rest:
        rest, bass_text = rest.split("/", 1)
        bass_part = _parse_root(bass_text)
        if not bass_part or bass_part[1]:
            raise ChordParseError(f"Unknown bass note in chord: {symbol}")
        bass = bass_part[0]

    approximated = False
    chord_type = EXACT_SUFFIXES.get(rest)
    if chord_type is None:
        chord_type = next((ctype for prefix, ctype in APPROXIMATE_PREFIXES if rest.startswith(prefix)), None)
        approximated = chord_type is not None
    if chord_type is None:
        raise ChordParseError(f"Unknown chord: {symbol}")

    chord = catalog[f"{root.value}{QUALITIES[chord_type].suffix}"]
    return ParsedChord(input=symbol, chord=chord, bass=bass, approximated=approximated)
