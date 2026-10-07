"""Turns a pasted song (chords over lyrics, ChordPro or ASCII tab) into a chord sequence."""

import re
from dataclasses import dataclass, field

from app.domain.catalog import parse
from app.domain.chord import ChordNode, ChordParseError
from app.style.tab_reader import is_tab_line, read_tab_block

SECTION_RE = re.compile(
    r"^\s*[\[(]?\s*(?P<name>intro|verso|estrofa|verse|pre-?coro|pre-?chorus|coro|estribillo|chorus|puente|bridge|"
    r"interludio|interlude|solo|outro|final|riff)\b[^\]):]*[\])]?\s*:?",
    re.IGNORECASE,
)
INLINE_CHORD_RE = re.compile(r"\[([^\]\s]{1,14})\]")
NOISE_TOKENS = {"|", "||", "-", "/", "%", "n.c.", "nc", "(", ")", "..."}
REPEAT_RE = re.compile(r"^[x×]\d+$|^\d+[x×]$|^\(?[x×]?\d+[x×]?\)?$", re.IGNORECASE)
CHORD_LINE_RATIO = 0.7


@dataclass
class Section:
    name: str
    chords: list[ChordNode] = field(default_factory=list)


@dataclass
class ParsedSong:
    title: str
    sections: list[Section]
    unknown: list[str]
    tab_chords: int

    @property
    def chords(self) -> list[ChordNode]:
        """All chords in order, with consecutive repeats collapsed."""
        result: list[ChordNode] = []
        for section in self.sections:
            for chord in section.chords:
                if not result or result[-1] != chord:
                    result.append(chord)
        return result


def _try_chord(token: str) -> ChordNode | None:
    try:
        return parse(token).chord
    except (ChordParseError, KeyError):
        return None


def _tokens(line: str) -> list[str]:
    tokens = []
    for raw in re.split(r"[\s,;]+", line.strip()):
        token = raw.strip("|.")
        if not token or token.lower() in NOISE_TOKENS or REPEAT_RE.match(token):
            continue
        parts = [part for part in token.split("-") if part]
        # "Am-F-C" is songbook shorthand; "Bm7-5" stays one chord.
        if len(parts) > 1 and all(_try_chord(part) for part in parts) and not _try_chord(token):
            tokens.extend(parts)
        else:
            tokens.append(token)
    return tokens


def chord_line(line: str) -> list[ChordNode] | None:
    """The chords of a line made (almost) only of chord symbols, else None."""
    tokens = _tokens(line)
    if not tokens:
        return None
    chords = [chord for chord in (_try_chord(token) for token in tokens) if chord]
    if not chords or len(chords) / len(tokens) < CHORD_LINE_RATIO:
        return None
    # A lone capitalised word ("Si", "La") at the start of a long lyric line is not a chord line.
    if len(tokens) == 1 and len(line.strip()) > 8:
        return None
    return chords


def parse_song(text: str, title: str = "Canción") -> ParsedSong:
    sections: list[Section] = [Section("")]
    unknown: list[str] = []
    tab_chords = 0
    lines = text.replace("\r\n", "\n").split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        if is_tab_line(line):
            block = []
            while index < len(lines) and is_tab_line(lines[index]):
                block.append(lines[index])
                index += 1
            chords = read_tab_block(block)
            tab_chords += len(chords)
            sections[-1].chords.extend(chords)
            continue
        index += 1

        stripped = line.strip()
        if not stripped:
            continue
        section = SECTION_RE.match(stripped)
        if section:
            sections.append(Section(section.group("name").lower()))
            stripped = stripped[section.end() :].strip()
            if not stripped:
                continue

        inline = INLINE_CHORD_RE.findall(stripped)
        if inline:
            for symbol in inline:
                chord = _try_chord(symbol)
                if chord:
                    sections[-1].chords.append(chord)
                elif not SECTION_RE.match(symbol):
                    unknown.append(symbol)
            continue

        chords = chord_line(stripped)
        if chords:
            sections[-1].chords.extend(chords)
            unknown.extend(token for token in _tokens(stripped) if not _try_chord(token))

    return ParsedSong(title=title, sections=[s for s in sections if s.chords], unknown=unknown[:20], tab_chords=tab_chords)
