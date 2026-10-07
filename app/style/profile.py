"""Learns a band's harmonic style from its songs.

Every chord is rewritten relative to its song's key as a *token*: the interval from the
tonic plus a coarse quality (``"10:maj"`` is ♭VII in any key). Working in tokens lets a
pattern learned from songs in E apply to a composition in C.

The profile keeps counts, not probabilities, so profiles stay small, can be merged and the
model can explain every suggestion ("♭VI → ♭VII → i in 5 songs").
"""

from collections import Counter
from dataclasses import dataclass

from app.domain.chord import NOTE_INDEX, NOTES, QUALITIES, ChordNode, ChordType
from app.domain.theory import Key, analyze_chord, detect_key, parse_key
from app.style.sheet_parser import ParsedSong

MAX_ORDER = 3
PATTERN_LENGTHS = range(3, 7)
MAX_PATTERNS = 12

QUALITY_OF: dict[ChordType, str] = {
    ChordType.MAJOR: "maj", ChordType.MAJ7: "maj", ChordType.ADD9: "maj", ChordType.SIX: "maj",
    ChordType.MINOR: "min", ChordType.MIN7: "min", ChordType.MIN6: "min",
    ChordType.DOM7: "dom", ChordType.DOM9: "dom",
    ChordType.DIM: "dim", ChordType.DIM7: "dim", ChordType.HALF_DIM7: "dim",
    ChordType.AUG: "aug",
    ChordType.SUS2: "sus", ChordType.SUS4: "sus",
    ChordType.POWER: "pow",
}
DEFAULT_TYPE = {
    "maj": ChordType.MAJOR, "min": ChordType.MINOR, "dom": ChordType.DOM7, "dim": ChordType.DIM,
    "aug": ChordType.AUG, "sus": ChordType.SUS4, "pow": ChordType.POWER,
}
DEGREES = ["I", "♭II", "II", "♭III", "III", "IV", "♯IV", "V", "♭VI", "VI", "♭VII", "VII"]
QUALITY_SUFFIX = {"maj": "", "min": "", "dom": "7", "dim": "°", "aug": "+", "sus": "sus", "pow": "5"}
COLOR_LABELS = {
    ChordType.MAJ7: "maj7", ChordType.ADD9: "add9", ChordType.SIX: "6", ChordType.MIN7: "m7",
    ChordType.MIN6: "m6", ChordType.DOM9: "9", ChordType.SUS2: "sus2", ChordType.SUS4: "sus4",
}


def token_of(chord: ChordNode, key: Key) -> str:
    return f"{key.degree(chord.root)}:{QUALITY_OF[chord.chord_type]}"


def numeral(token: str) -> str:
    interval, quality = token.split(":")
    name = DEGREES[int(interval)]
    if quality in ("min", "dim"):
        name = name.lower()
    return name + QUALITY_SUFFIX[quality]


def realize(token: str, key: Key, colors: dict[str, dict[str, int]] | None = None) -> str:
    """Chord id of a token in ``key``, in the colour the band plays it most (♭VI as maj7…)."""
    interval, quality = token.split(":")
    root = NOTES[(NOTE_INDEX[key.tonic] + int(interval)) % 12]
    chord_type = DEFAULT_TYPE[quality]
    played = (colors or {}).get(token)
    if played:
        chord_type = ChordType(max(played.items(), key=lambda item: (item[1], item[0] == chord_type.value))[0])
    return f"{root.value}{QUALITIES[chord_type].suffix}"


@dataclass
class SongTokens:
    title: str
    key: Key
    chords: list[ChordNode]
    tokens: list[str]


def tokenize_song(song: ParsedSong, key_hint: str | None = None) -> SongTokens | None:
    chords = song.chords
    if len(chords) < 2:
        return None
    key = parse_key(key_hint) or detect_key(chords).key
    return SongTokens(song.title, key, chords, [token_of(chord, key) for chord in chords])


def _ctx(tokens: list[str] | tuple[str, ...]) -> str:
    return "|".join(tokens)


def _canonical_rotation(pattern: tuple[str, ...]) -> tuple[str, ...]:
    return min(pattern[i:] + pattern[:i] for i in range(len(pattern)))


def _contains(longer: tuple[str, ...], shorter: tuple[str, ...]) -> bool:
    size = len(shorter)
    return any(longer[i:i + size] == shorter for i in range(len(longer) - size + 1))


def _shifted(listed: tuple[str, ...], gram: tuple[str, ...]) -> bool:
    """True when ``gram`` overlaps ``listed`` in all but one chord at either end."""
    overlap = len(gram) - 1
    return overlap >= 2 and len(listed) >= len(gram) and (
        _contains(listed, gram[1:]) or _contains(listed, gram[:-1])
    )


def mine_patterns(songs: list[SongTokens]) -> list[dict]:
    """Recurring chord sequences, longest and most widespread first.

    Rotations of the same loop (i ♭VI ♭III ♭VII / ♭VI ♭III ♭VII i) count once, and a
    sequence is dropped when a longer one carries the same evidence.
    """
    counts: Counter[tuple[str, ...]] = Counter()
    song_sets: dict[tuple[str, ...], set[int]] = {}
    starts: Counter[str] = Counter(song.tokens[0] for song in songs)
    for index, song in enumerate(songs):
        for size in PATTERN_LENGTHS:
            for i in range(len(song.tokens) - size + 1):
                gram = tuple(song.tokens[i:i + size])
                if len(set(gram)) < 2:
                    continue
                counts[gram] += 1
                song_sets.setdefault(gram, set()).add(index)

    candidates = [gram for gram, count in counts.items() if count >= 2]

    # One representative per loop: the most played rotation, preferring one that starts where songs start.
    by_rotation: dict[tuple[str, ...], tuple[str, ...]] = {}
    for gram in candidates:
        canonical = _canonical_rotation(gram)
        current = by_rotation.get(canonical)
        rank = (len(song_sets[gram]), counts[gram], starts[gram[0]], gram[0].startswith("0:"))
        if current is None or rank > (len(song_sets[current]), counts[current], starts[current[0]], current[0].startswith("0:")):
            by_rotation[canonical] = gram
    candidates = list(by_rotation.values())

    kept = [
        gram for gram in candidates
        if not any(
            len(other) > len(gram) and _contains(other, gram)
            and len(song_sets[other]) >= len(song_sets[gram]) and counts[other] * 4 >= counts[gram] * 3
            for other in candidates
        )
    ]
    kept.sort(key=lambda gram: (len(song_sets[gram]), counts[gram] * len(gram)), reverse=True)

    patterns = []
    loops: list[tuple[str, ...]] = []
    listed_grams: list[tuple[str, ...]] = []
    for gram in kept:
        # A longer run that only walks around a loop already listed adds nothing.
        if any(_contains(loop * (len(gram) // len(loop) + 2), gram) for loop in loops):
            continue
        # Nor does the same phrase shifted by one chord.
        if any(_shifted(listed, gram) for listed in listed_grams):
            continue
        listed_grams.append(gram)
        loop = any(_contains(tuple(song.tokens), gram + gram) for song in songs)
        if loop:
            loops.append(gram)
        if len(patterns) == MAX_PATTERNS:
            break
        patterns.append({
            "tokens": list(gram),
            "numerals": [numeral(token) for token in gram],
            "count": counts[gram],
            "songs": len(song_sets[gram]),
            "loop": loop,
        })
    return patterns


def _percent(part: float, whole: float) -> int:
    return round(100 * part / whole) if whole else 0


def describe(songs: list[SongTokens], usage: dict[str, dict], qualities: Counter, colors: Counter, roles: Counter) -> list[str]:
    """Plain-language traits of the band's harmony."""
    traits: list[str] = []
    total_songs = len(songs)
    total_chords = sum(qualities.values())
    minor_songs = sum(1 for song in songs if song.key.mode == "minor")
    if minor_songs * 3 >= total_songs * 2:
        traits.append(f"Compone sobre todo en menor ({minor_songs} de {total_songs} canciones).")
    elif minor_songs * 3 <= total_songs:
        traits.append(f"Compone sobre todo en mayor ({total_songs - minor_songs} de {total_songs} canciones).")
    else:
        traits.append(f"Alterna entre mayor y menor ({minor_songs} de {total_songs} canciones en menor).")

    average = sum(len(set(song.tokens)) for song in songs) / total_songs
    traits.append(f"Usa unos {average:.0f} acordes distintos por canción.")

    signature = sorted(
        (
            (data["songs"], token) for token, data in usage.items()
            if data["role"] in ("borrowed", "chromatic", "secondary_dominant") and data["songs"] * 10 >= total_songs * 3
        ),
        reverse=True,
    )
    for song_count, token in signature[:3]:
        traits.append(f"{numeral(token)} es una firma: aparece en {song_count} de {total_songs} canciones.")

    if _percent(qualities["pow"], total_chords) >= 20:
        traits.append(f"Mucho power chord: {_percent(qualities['pow'], total_chords)}% de los acordes.")
    if _percent(qualities["dom"], total_chords) >= 20:
        traits.append(f"Le gustan las séptimas de dominante ({_percent(qualities['dom'], total_chords)}% de los acordes).")
    if _percent(qualities["sus"], total_chords) >= 10:
        traits.append(f"Suspende acordes a menudo (sus2/sus4: {_percent(qualities['sus'], total_chords)}%).")
    for color, count in colors.most_common(2):
        if _percent(count, total_chords) >= 12:
            traits.append(f"Color favorito: {color} ({_percent(count, total_chords)}% de los acordes).")
    outside = roles["borrowed"] + roles["chromatic"]
    if _percent(outside, total_chords) >= 25:
        traits.append(f"Sale seguido de la tonalidad: {_percent(outside, total_chords)}% de acordes prestados o cromáticos.")
    elif _percent(outside, total_chords) <= 5:
        traits.append("Casi siempre se queda dentro de la tonalidad.")
    return traits


def learn_profile(name: str, songs: list[SongTokens]) -> dict:
    """Counts n-gram transitions (orders 0-3), colours, roles and patterns."""
    transitions: dict[str, dict[str, dict[str, int]]] = {}
    unigrams: Counter[str] = Counter()
    song_support: dict[str, set[int]] = {}
    usage: dict[str, dict] = {}
    qualities: Counter[str] = Counter()
    colors_by_token: dict[str, Counter[str]] = {}
    color_labels: Counter[str] = Counter()
    roles: Counter[str] = Counter()
    starts: Counter[str] = Counter()
    endings: Counter[str] = Counter()

    for index, song in enumerate(songs):
        starts[song.tokens[0]] += 1
        endings[_ctx(song.tokens[-2:])] += 1
        for chord, token in zip(song.chords, song.tokens):
            unigrams[token] += 1
            qualities[token.split(":")[1]] += 1
            colors_by_token.setdefault(token, Counter())[chord.chord_type.value] += 1
            if chord.chord_type in COLOR_LABELS:
                color_labels[COLOR_LABELS[chord.chord_type]] += 1
            role = analyze_chord(chord, song.key).role
            roles[role] += 1
            entry = usage.setdefault(token, {"count": 0, "songs": 0, "role": role, "_songs": set()})
            entry["count"] += 1
            entry["_songs"].add(index)

        for position in range(1, len(song.tokens)):
            following = song.tokens[position]
            for order in range(1, MAX_ORDER + 1):
                if position - order < 0:
                    break
                context = _ctx(song.tokens[position - order:position])
                bucket = transitions.setdefault(context, {"n": {}, "s": {}})
                bucket["n"][following] = bucket["n"].get(following, 0) + 1
                key = f"{context}>{following}"
                if index not in song_support.setdefault(key, set()):
                    song_support[key].add(index)
                    bucket["s"][following] = bucket["s"].get(following, 0) + 1

    for entry in usage.values():
        entry["songs"] = len(entry.pop("_songs"))

    return {
        "version": 1,
        "name": name,
        "songs": [
            {"title": song.title, "key": song.key.id, "keyLabel": song.key.label, "chords": [chord.id for chord in song.chords]}
            for song in songs
        ],
        "modes": {"major": sum(1 for s in songs if s.key.mode == "major"), "minor": sum(1 for s in songs if s.key.mode == "minor")},
        "unigrams": dict(unigrams),
        "transitions": transitions,
        "colors": {token: dict(counter) for token, counter in colors_by_token.items()},
        "usage": {token: {**data, "numeral": numeral(token)} for token, data in sorted(usage.items(), key=lambda item: -item[1]["count"])},
        "starts": dict(starts),
        "endings": dict(endings),
        "patterns": mine_patterns(songs),
        "traits": describe(songs, usage, qualities, color_labels, roles),
    }
