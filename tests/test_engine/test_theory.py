import pytest

from app.domain.catalog import BY_ID, parse
from app.domain.chord import ChordParseError
from app.domain.theory import analyze_chord, detect_key, parse_key, suggest_substitutions


@pytest.mark.parametrize(
    ("symbol", "expected", "bass", "approximated"),
    [
        ("Bbmaj7", "A#maj7", None, False),
        ("F#m7(b5)", "F#m7b5", None, False),
        ("D/F#", "D", "F#", False),
        ("SOLm", "Gm", None, False),
        ("DOadd9", "Cadd9", None, False),
        ("SOL/SI", "G", "B", False),
        ("Dsus", "Dsus4", None, False),
        ("E7#9", "E7", None, True),
        ("Fmaj9", "Fmaj7", None, True),
        ("A5", "A5", None, False),
    ],
)
def test_parse_chord_symbols(symbol, expected, bass, approximated):
    parsed = parse(symbol)
    assert parsed.chord.id == expected
    assert (parsed.bass.value if parsed.bass else None) == bass
    assert parsed.approximated is approximated


def test_parse_rejects_garbage():
    with pytest.raises(ChordParseError):
        parse("H7")


def test_seventh_chords_have_four_notes():
    assert [note.value for note in BY_ID["G7"].notes] == ["G", "B", "D", "F"]
    assert [note.value for note in BY_ID["Cmaj7"].notes] == ["C", "E", "G", "B"]


@pytest.mark.parametrize(
    ("progression", "key"),
    [
        ("C G Am F", "C"),
        ("Dm7 G7 Cmaj7", "C"),
        ("Am G F E", "Am"),
        ("Bm G D A", "Bm"),
        ("A7 D7 A7 E7", "A"),
    ],
)
def test_detect_key(progression, key):
    chords = [parse(symbol).chord for symbol in progression.split()]
    assert detect_key(chords).key.id == key


def test_roman_numerals_and_roles():
    key = parse_key("C")
    assert analyze_chord(BY_ID["G7"], key).numeral == "V7"
    assert analyze_chord(BY_ID["Dm"], key).numeral == "ii"
    secondary = analyze_chord(BY_ID["A7"], key)
    assert secondary.role == "secondary_dominant"
    assert secondary.numeral == "V7/ii"
    borrowed = analyze_chord(BY_ID["Fm"], key)
    assert borrowed.role == "borrowed"
    assert borrowed.numeral == "iv"


def test_substitutions_include_tritone_for_dominants():
    subs = suggest_substitutions(BY_ID["G7"], parse_key("C"), BY_ID)
    assert any(sub.chord == "C#7" and sub.kind == "tritono" for sub in subs)
