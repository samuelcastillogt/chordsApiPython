import pytest

from app.domain.chord import ChordNode
from app.engine.connection_engine import find_connections, score_connection


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


def test_g7_to_c_dominant_chain(all_chords):
    g7 = next(c for c in all_chords if c.id == "G7")
    c = next(c for c in all_chords if c.id == "C")
    conn = score_connection(g7, c, "C")
    assert conn.category == "natural"
    chain = next((b for b in conn.breakdown if b.name == "dominant_chain"), None)
    assert chain is not None
    assert chain.raw_score == 100.0


def test_distinct_results_skip_colour_variants_of_the_same_chord(all_chords):
    c = next(c for c in all_chords if c.id == "C")
    results = find_connections(c, all_chords, tonality="C", max_results=20)
    groups = [(r.target.root, r.target.family) for r in results]
    assert len(groups) == len(set(groups))
    assert not any(r.target.root == c.root and r.target.family == "major" for r in results)
