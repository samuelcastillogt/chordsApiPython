import pytest

from app.domain.chord import ChordNode
from app.engine.connection_engine import find_connections, intent_for, score_connection
from app.engine.criteria import dominant_chain


@pytest.fixture
def all_chords():
    return ChordNode.build_all()


def test_c_to_cm_has_two_shared_notes(all_chords):
    c = next(c for c in all_chords if c.id == "C")
    cm = next(c for c in all_chords if c.id == "Cm")
    conn = score_connection(c, cm, "C")
    assert conn.total > 50


def test_c_to_c_same_chord_not_included(all_chords):
    c = next(c for c in all_chords if c.id == "C")
    results = find_connections(c, all_chords)
    assert not any(r.target.id == "C" for r in results)


def test_min_score_filter(all_chords):
    c = next(c for c in all_chords if c.id == "C")
    results = find_connections(c, all_chords, min_score=80)
    assert all(r.total >= 80 for r in results)


def test_max_results_respected(all_chords):
    c = next(c for c in all_chords if c.id == "C")
    results = find_connections(c, all_chords, max_results=5)
    assert len(results) <= 5


@pytest.mark.parametrize(
    ("score", "intent"),
    [(100, "safe"), (70, "safe"), (69.9, "interesting"), (50, "interesting"), (49.9, "bold"), (0, "bold")],
)
def test_intent_thresholds_are_deterministic(score, intent):
    assert intent_for(score) == intent


@pytest.mark.parametrize(
    ("dominant", "tonic"),
    [
        ("C7", "F"),
        ("G7", "C"),
        ("D7", "G"),
        ("A7", "D"),
        ("E7", "A"),
        ("B7", "E"),
        ("F#7", "B"),
        ("C#7", "F#"),
        ("G#7", "C#"),
        ("D#7", "G#"),
        ("A#7", "D#"),
        ("F7", "A#"),
    ],
)
def test_all_v7_to_i_resolutions_are_dominant_chains(all_chords, dominant, tonic):
    source = next(chord for chord in all_chords if chord.id == dominant)
    target = next(chord for chord in all_chords if chord.id == tonic)

    score, _ = dominant_chain(source, target)

    assert score == 100.0


def test_distinct_results_skip_colour_variants_of_the_same_chord(all_chords):
    c = next(c for c in all_chords if c.id == "C")
    results = find_connections(c, all_chords, tonality="C", max_results=20)
    groups = [(r.target.root, r.target.family) for r in results]
    assert len(groups) == len(set(groups))
    assert not any(r.target.root == c.root and r.target.family == "major" for r in results)
