from enum import Enum
from dataclasses import dataclass


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


NOTES = [Note.C, Note.CSHARP, Note.D, Note.DSHARP, Note.E, Note.F, Note.FSHARP, Note.G, Note.GSHARP, Note.A, Note.ASHARP, Note.B]
NOTE_INDEX = {note: i for i, note in enumerate(NOTES)}

CIRCLE_OF_FIFTHS = [Note.C, Note.G, Note.D, Note.A, Note.E, Note.B, Note.FSHARP, Note.DSHARP, Note.ASHARP, Note.F, Note.CSHARP, Note.GSHARP]


def transpose_note(note: Note, semitones: int) -> Note:
    return NOTES[(NOTE_INDEX[note] + semitones) % 12]


def build_triad(root: Note, chord_type: ChordType) -> tuple[Note, Note, Note]:
    if chord_type == ChordType.MAJOR:
        return (root, transpose_note(root, 4), transpose_note(root, 7))
    if chord_type == ChordType.MINOR:
        return (root, transpose_note(root, 3), transpose_note(root, 7))
    if chord_type == ChordType.DIM:
        return (root, transpose_note(root, 3), transpose_note(root, 6))
    if chord_type == ChordType.AUG:
        return (root, transpose_note(root, 4), transpose_note(root, 8))
    if chord_type == ChordType.DOM7:
        return (root, transpose_note(root, 4), transpose_note(root, 7))
    if chord_type == ChordType.DIM7:
        return (root, transpose_note(root, 3), transpose_note(root, 6))
    raise ValueError(f"Unknown chord type: {chord_type}")


@dataclass
class ChordNode:
    root: Note
    chord_type: ChordType
    triad: tuple[Note, Note, Note]
    circle_position: int

    @property
    def id(self) -> str:
        base = self.root.value
        suffix = {
            ChordType.MAJOR: "",
            ChordType.MINOR: "m",
            ChordType.DIM: "°",
            ChordType.AUG: "+",
            ChordType.DOM7: "7",
            ChordType.DIM7: "°7",
        }
        return f"{base}{suffix[self.chord_type]}"

    @classmethod
    def build_all(cls) -> list["ChordNode"]:
        chords = []
        for i, root in enumerate(CIRCLE_OF_FIFTHS):
            for ctype in [ChordType.MAJOR, ChordType.MINOR, ChordType.DIM, ChordType.AUG, ChordType.DOM7, ChordType.DIM7]:
                triad = build_triad(root, ctype)
                chords.append(cls(root=root, chord_type=ctype, triad=triad, circle_position=i))
        return chords
