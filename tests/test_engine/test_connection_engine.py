import pytest
from app.domain.chord import ChordNode, ChordType
from app.engine.connection_engine import find_connections


@pytest.fixture
def all_chords():
    return ChordNode.build_all()


def test_c_to_cm_has_two_shared_notes(all_chords):
    c = next(c for c in all_chords if c.id == "C")
    cm = next(c for c in all_chords if c.id == "Cm")
    results = find_connections(c, all_chords, tonality="C")
    conn = next((r for r in results if r.target.id == "Cm"), None)
    assert conn is not None
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
    results = find_connections(g7, all_chords)
    conn = next((r for r in results if r.target.id == "C"), None)
    assert conn is not None
    chain = next((b for b in conn.breakdown if b.name == "dominant_chain"), None)
    assert chain is not None
    assert chain.raw_score == 100.0
