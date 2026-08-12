from app.domain.chord import ChordNode, ChordType
from app.domain.connection import ConnectionScore, CriterionScore
from app.engine.weights import WEIGHTS
from app.engine import criteria

_score_cache: dict[tuple[str, str, str | None], ConnectionScore] = {}


def find_connections(
    current: ChordNode,
    all_chords: list[ChordNode],
    tonality: str | None = None,
    min_score: float = 0,
    max_results: int = 12,
) -> list[ConnectionScore]:
    results: list[ConnectionScore] = []
    for candidate in all_chords:
        if candidate.id == current.id:
            continue

        cache_key = (current.id, candidate.id, tonality)
        cached = _score_cache.get(cache_key)
        if cached:
            if cached.total >= min_score:
                results.append(cached)
            continue

        scores: list[CriterionScore] = []

        raw, detail = criteria.shared_notes(current, candidate)
        scores.append(CriterionScore("shared_notes", WEIGHTS["shared_notes"], raw, raw * WEIGHTS["shared_notes"], detail))

        raw, detail = criteria.circle_distance(current, candidate)
        scores.append(CriterionScore("circle_distance", WEIGHTS["circle_distance"], raw, raw * WEIGHTS["circle_distance"], detail))

        raw, detail = criteria.voice_movement(current, candidate)
        scores.append(CriterionScore("voice_movement", WEIGHTS["voice_movement"], raw, raw * WEIGHTS["voice_movement"], detail))

        raw, detail = criteria.transformation_type(current, candidate)
        scores.append(CriterionScore("transformation", WEIGHTS["transformation"], raw, raw * WEIGHTS["transformation"], detail))

        raw, detail = criteria.tonal_function(current, candidate, tonality)
        scores.append(CriterionScore("tonal_function", WEIGHTS["tonal_function"], raw, raw * WEIGHTS["tonal_function"], detail))

        raw, detail = criteria.dominant_chain(current, candidate)
        scores.append(CriterionScore("dominant_chain", WEIGHTS["dominant_chain"], raw, raw * WEIGHTS["dominant_chain"], detail))

        raw, detail = criteria.glue_magic(current, candidate)
        scores.append(CriterionScore("glue_magic", WEIGHTS["glue_magic"], raw, raw * WEIGHTS["glue_magic"], detail))

        total = round(sum(s.weighted_score for s in scores), 1)

        category = "natural" if total >= 80 else "media" if total >= 50 else "tensa" if total >= 20 else "extrema"

        connection = ConnectionScore(
            source=current, target=candidate, total=total, category=category, breakdown=scores
        )
        _score_cache[cache_key] = connection
        if total >= min_score:
            results.append(connection)

    results.sort(key=lambda r: r.total, reverse=True)
    return results[:max_results]
