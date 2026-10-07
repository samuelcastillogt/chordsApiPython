"""Reads ASCII guitar tablature and recognises the chords it plays.

A tab block is a run of string lines (``e|--0--3--|``). Bar lines split it into segments;
inside a segment, columns where three or more strings sound together are chord stacks and
single notes after a stack belong to it (an arpeggio). A segment without stacks is read
as one arpeggiated chord. Each group of notes is matched against the chord catalog.
"""

import re
from dataclasses import dataclass

from app.domain.catalog import ALL_CHORDS
from app.domain.chord import NOTE_INDEX, ChordNode, ChordType, _parse_root

TAB_LINE_RE = re.compile(r"^\s*(?P<label>[A-Ga-g][#b]?)?\s*(?P<sep>[|:])?(?P<body>[-0-9xXhpbrs/\\~|().<>^*=v ]*-[-0-9xXhpbrs/\\~|().<>^*=v ]*)$")
STANDARD_GUITAR = ["E", "B", "G", "D", "A", "E"]
MIN_DASHES = 4
STACK_SIZE = 3
MIN_MATCH = 0.35
UNBARRED_WIDTH = 16

# Chords a tab can be recognised as: the triad and seventh vocabulary plus power and sus chords.
RECOGNISABLE = {
    ChordType.MAJOR, ChordType.MINOR, ChordType.DIM, ChordType.AUG, ChordType.DOM7, ChordType.MAJ7,
    ChordType.MIN7, ChordType.HALF_DIM7, ChordType.DIM7, ChordType.SUS2, ChordType.SUS4, ChordType.POWER,
}
CANDIDATES = [chord for chord in ALL_CHORDS if chord.chord_type in RECOGNISABLE]


@dataclass(frozen=True)
class TabNote:
    column: int
    string: int  # 0 = top line (highest string)
    midi: int

    @property
    def pitch_class(self) -> int:
        return self.midi % 12


def is_tab_line(line: str) -> bool:
    match = TAB_LINE_RE.match(line.rstrip())
    return bool(match) and match.group("body").count("-") >= MIN_DASHES


def _open_strings(labels: list[str | None]) -> list[int]:
    """MIDI pitch of each open string, top line first (standard tuning when unlabelled)."""
    count = len(labels)
    names: list[str] = [label for label in labels if label] if all(labels) else (STANDARD_GUITAR if count == 6 else STANDARD_GUITAR[:count])
    pitches: list[int] = []
    previous = 65  # Just above the high E (64), so the top string lands on it.
    for name in names:
        parsed = _parse_root(name.upper() if len(name) == 1 else name[0].upper() + name[1:])
        pc = NOTE_INDEX[parsed[0]] if parsed else 4
        midi = previous - 1
        while midi % 12 != pc:
            midi -= 1
        pitches.append(midi)
        previous = midi
    return pitches


def _read_block(lines: list[str]) -> tuple[list[str], list[int]]:
    """Strips the string labels; returns aligned bodies and open-string pitches."""
    labels: list[str | None] = []
    bodies: list[str] = []
    for line in lines:
        match = TAB_LINE_RE.match(line.rstrip())
        assert match
        labels.append(match.group("label"))
        bodies.append(match.group("body"))
    return bodies, _open_strings(labels)


def _notes(bodies: list[str], open_strings: list[int]) -> list[TabNote]:
    notes: list[TabNote] = []
    for string, body in enumerate(bodies):
        for match in re.finditer(r"\d{1,2}", body):
            start = match.start()
            if start > 0 and body[start - 1] in "xX":
                continue  # "x4" repeat marks, not frets.
            fret = int(match.group())
            if fret > 24:
                fret = int(match.group()[0])
            notes.append(TabNote(start, string, open_strings[string] + fret))
    return notes


def _bar_columns(bodies: list[str]) -> list[int]:
    width = max(len(body) for body in bodies)
    bars = []
    for column in range(width):
        hits = sum(1 for body in bodies if column < len(body) and body[column] == "|")
        if hits * 2 >= len(bodies):
            bars.append(column)
    return bars


def _segments(bodies: list[str], notes: list[TabNote]) -> list[list[TabNote]]:
    bars = _bar_columns(bodies)
    width = max(len(body) for body in bodies)
    edges = bars if bars else list(range(0, width, UNBARRED_WIDTH))
    edges = sorted(set([0, *edges, width + 1]))
    segments = []
    for start, end in zip(edges, edges[1:]):
        segment = sorted((note for note in notes if start <= note.column < end), key=lambda note: note.column)
        if segment:
            segments.append(segment)
    return segments


def identify_chord(notes: list[TabNote]) -> ChordNode | None:
    """Best catalog chord for a group of notes: covers the most weight, wastes the least."""
    if not notes:
        return None
    weights: dict[int, float] = {}
    for note in notes:
        weights[note.pitch_class] = weights.get(note.pitch_class, 0.0) + 1.0
    bass = min(notes, key=lambda note: note.midi).pitch_class
    weights[bass] += 0.5
    total = sum(weights.values())
    if len(weights) < 2:
        return None

    best: tuple[float, ChordNode] | None = None
    for chord in CANDIDATES:
        tones = chord.pitch_classes
        root = NOTE_INDEX[chord.root]
        if root not in weights:
            continue
        covered = sum(weight for pc, weight in weights.items() if pc in tones)
        foreign = total - covered
        missing = len(tones - weights.keys())
        score = (covered - foreign) / total - 0.18 * missing - 0.02 * len(tones)
        if bass == root:
            score += 0.12
        if best is None or score > best[0]:
            best = (score, chord)
    return best[1] if best and best[0] >= MIN_MATCH else None


def _segment_chords(segment: list[TabNote]) -> list[ChordNode]:
    columns: dict[int, list[TabNote]] = {}
    for note in segment:
        columns.setdefault(note.column, []).append(note)
    stacks = [column for column, items in columns.items() if len(items) >= STACK_SIZE]
    if not stacks:
        chord = identify_chord(segment)
        return [chord] if chord else []

    # Each stack owns the single notes that ring after it (until the next stack).
    groups: list[list[TabNote]] = []
    boundaries = sorted(stacks) + [10**9]
    leading = [note for note in segment if note.column < boundaries[0]]
    for start, end in zip(boundaries, boundaries[1:]):
        groups.append([note for note in segment if start <= note.column < end])
    if leading and groups:
        groups[0] = leading + groups[0]
    chords: list[ChordNode] = []
    for group in groups:
        chord = identify_chord(group)
        if chord and (not chords or chords[-1] != chord):
            chords.append(chord)
    return chords


def read_tab_block(lines: list[str]) -> list[ChordNode]:
    """Chords played by one tab block, in order (consecutive repeats collapsed)."""
    if len(lines) < 5:
        return []  # Bass tabs (4 strings) carry the root but not the chord quality.
    bodies, open_strings = _read_block(lines)
    notes = _notes(bodies, open_strings)
    chords: list[ChordNode] = []
    for segment in _segments(bodies, notes):
        for chord in _segment_chords(segment):
            if not chords or chords[-1] != chord:
                chords.append(chord)
    return chords
