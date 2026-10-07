from functools import lru_cache

from app.domain.chord import ChordNode
from app.domain.connection import ConnectionScore, CriterionScore
from app.engine import criteria
from app.engine.weights import WEIGHTS

CRITERIA = (
    ("shared_notes", lambda a, b, key: criteria.shared_notes(a, b)),
    ("circle_distance", lambda a, b, key: criteria.circle_distance(a, b)),
    ("voice_movement", lambda a, b, key: criteria.voice_movement(a, b)),
    ("transformation", lambda a, b, key: criteria.transformation_type(a, b)),
    ("tonal_function", lambda a, b, key: criteria.tonal_function(a, b, key)),
    ("dominant_chain", lambda a, b, key: criteria.dominant_chain(a, b)),
    ("glue_magic", lambda a, b, key: criteria.glue_magic(a, b)),
)


def category_for(total: float) -> str:
    return "natural" if total >= 70 else "media" if total >= 50 else "tensa" if total >= 30 else "extrema"


@lru_cache(maxsize=65536)
def score_connection(source: ChordNode, target: ChordNode, tonality: str | None = None) -> ConnectionScore:
    breakdown = []
    for name, evaluate in CRITERIA:
        raw, detail = evaluate(source, target, tonality)
        breakdown.append(CriterionScore(name, WEIGHTS[name], raw, raw * WEIGHTS[name], detail))
    total = round(sum(item.weighted_score for item in breakdown), 1)
    return ConnectionScore(source=source, target=target, total=total, category=category_for(total), breakdown=breakdown)


def find_connections(
    current: ChordNode,
    all_chords: list[ChordNode],
    tonality: str | None = None,
    min_score: float = 0,
    max_results: int = 12,
    distinct: bool = True,
) -> list[ConnectionScore]:
    """Ranks candidate next chords.

    With ``distinct`` only the best voicing per root and chord family is kept,
    so C does not recommend C7, Cmaj7 and C6 as if they were different moves.
    """
    scored = [score_connection(current, candidate, tonality) for candidate in all_chords if candidate.id != current.id]
    scored.sort(key=lambda item: item.total, reverse=True)

    results: list[ConnectionScore] = []
    seen: set[tuple[str, str]] = set()
    for connection in scored:
        target = connection.target
        if connection.total < min_score:
            break
        if distinct:
            group = (target.root.value, target.family)
            if target.root == current.root and target.family == current.family:
                continue
            if group in seen:
                continue
            seen.add(group)
        results.append(connection)
        if len(results) >= max_results:
            break
    return results
