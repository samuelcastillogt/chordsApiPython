from fastapi.testclient import TestClient

from app.domain.theory import parse_key
from app.main import app
from app.style.model import distribution, suggest
from app.style.profile import learn_profile, numeral, realize, tokenize_song
from app.style.sheet_parser import chord_line, parse_song
from app.style.tab_reader import identify_chord, read_tab_block, TabNote

client = TestClient(app)

ARPEGGIO_TAB = """
e|-----0-----|-----3-----|-----0-----|
B|---1---1---|---0---0---|---1---1---|
G|-0-------0-|-0-------0-|-2-------2-|
D|-----------|-----------|-2---------|
A|-3---------|-----------|-0---------|
E|-----------|-3---------|-----------|
"""

POWER_TAB = """
e|-------------------------|
B|-------------------------|
G|-------------------------|
D|--7-7-7---5-5-5---3-3----|
A|--7-7-7---5-5-5---3-3----|
E|--5-5-5---3-3-3---1-1----|
"""

SONGS = [
    {"title": "Uno", "text": "[Intro]\nAm F C G\n[Verso]\nAm F C G\nAm F C G\n[Coro]\nF G Am\nF G E7 Am"},
    {"title": "Dos", "text": "Em C G D\nEm C G D\nC D Em\nC D B7 Em"},
    {"title": "Tres", "text": "Dm Bb F C\nDm Bb F C\nBb C Dm"},
]


def profile_from(songs=SONGS):
    tokens = [tokenize_song(parse_song(song["text"], song["title"])) for song in songs]
    return learn_profile("Banda", [item for item in tokens if item])


def ids(chords):
    return [chord.id for chord in chords]


def test_chord_lines_are_told_apart_from_lyrics():
    assert ids(chord_line("Am   F   C   G")) == ["Am", "F", "C", "G"]
    assert ids(chord_line("| Dm  G/B | C  E7 | x2")) == ["Dm", "G", "C", "E7"]
    assert ids(chord_line("Bb-F-C")) == ["A#", "F", "C"]
    assert chord_line("Mi corazón late por ti") is None
    assert chord_line("Si tú me dices que sí") is None
    assert chord_line("A love so true") is None


def test_parse_song_reads_sections_inline_chords_and_tabs():
    song = parse_song("Intro: Am F\n[Coro]\n[C]Hoy te [G]vi\n" + ARPEGGIO_TAB)

    assert [section.name for section in song.sections] == ["intro", "coro"]
    assert ids(song.chords) == ["Am", "F", "C", "G", "C", "G", "Am"]
    assert song.tab_chords == 3


def test_tab_reader_recognises_arpeggios_and_power_chords():
    lines = [line for line in ARPEGGIO_TAB.strip().split("\n")]
    assert ids(read_tab_block(lines)) == ["C", "G", "Am"]
    assert ids(read_tab_block(POWER_TAB.strip().split("\n"))) == ["A5", "G5", "F5"]


def test_tab_reader_ignores_bass_tabs_and_single_notes():
    bass = ["G|-----|", "D|-----|", "A|--0--|", "E|--3--|"]
    assert read_tab_block(bass) == []
    assert identify_chord([TabNote(0, 0, 64)]) is None


def test_tokens_are_relative_to_the_key():
    key = parse_key("Cm")
    assert realize("8:maj", key) == "G#"
    assert realize("8:maj", key, {"8:maj": {"maj7": 3, "major": 1}}) == "G#maj7"
    assert numeral("10:maj") == "♭VII"
    assert numeral("2:dim") == "ii°"


def test_profile_finds_the_band_loop_in_any_key():
    profile = profile_from()

    assert [song["key"] for song in profile["songs"]] == ["Am", "Em", "Dm"]
    assert profile["modes"] == {"major": 0, "minor": 3}
    top = profile["patterns"][0]
    assert top["numerals"] == ["i", "♭VI", "♭III", "♭VII"]
    assert top["songs"] == 3 and top["loop"] is True
    assert any("menor" in trait for trait in profile["traits"])


def test_distribution_prefers_long_contexts_the_band_used():
    profile = profile_from()
    after_vi = distribution(profile, ["0:min", "8:maj"])
    assert max(after_vi, key=after_vi.get) == "3:maj"
    assert abs(sum(after_vi.values()) - 1) < 1e-9


def test_suggest_blends_style_with_the_engine_and_explains_it():
    profile = profile_from()
    result = suggest(profile, [parse("Cm"), parse("G#")], parse_key("Cm"), weight=0.7)

    best = result["connections"][0]
    assert best["target"] == "D#"
    assert best["style"]["numeral"] == "♭III"
    assert "♭VI" in best["style"]["evidence"]
    assert [step["numeral"] for step in result["phrase"]][:2] == ["♭III", "♭VII"]

    engine_only = suggest(profile, [parse("Cm"), parse("G#")], parse_key("Cm"), weight=0)
    assert all(item["score"] == item["engineScore"] for item in engine_only["connections"])


def parse(symbol):
    from app.domain.catalog import find_chord

    return find_chord(symbol)


def test_style_api_round_trip():
    parsed = client.post("/api/v1/style/parse", json={"text": "Am F C G\nAm F C G", "title": "Demo"})
    assert parsed.status_code == 200
    assert parsed.json()["chords"] == ["Am", "F", "C", "G", "Am", "F", "C", "G"]
    assert parsed.json()["key"] == "Am"

    learned = client.post("/api/v1/style/learn", json={"name": "Banda", "songs": [*SONGS, {"title": "Vacía", "text": "solo letra"}]})
    assert learned.status_code == 200
    profile = learned.json()
    assert profile["skipped"] == ["Vacía"]

    suggestion = client.post("/api/v1/style/suggest", json={"profile": profile, "history": ["Cm", "Ab"], "tonality": "Cm"})
    assert suggestion.status_code == 200
    body = suggestion.json()
    assert body["context"] == ["i", "♭VI"]
    assert body["connections"][0]["target"] == "D#"
    assert body["connections"][0]["style"]["evidence"]


def test_style_learn_rejects_songs_without_chords():
    response = client.post("/api/v1/style/learn", json={"name": "Nada", "songs": [{"text": "hola mundo"}]})
    assert response.status_code == 422


def test_suggest_keeps_one_colour_per_degree():
    result = suggest(profile_from(), [parse("Cm")], parse_key("Cm"))
    numerals = [item["style"]["numeral"] for item in result["connections"]]
    assert len(numerals) == len(set(numerals))
