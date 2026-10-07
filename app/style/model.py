"""Predicts the next chord "as the band would play it" and blends it with the harmonic engine.

The style model is a variable-order Markov chain over key-relative tokens (orders 0-3) with
Witten-Bell interpolation: a long context the band has used many times dominates, an
unseen or rare one falls back smoothly to shorter contexts and finally to how often the
band plays each chord at all.
"""

from dataclasses import dataclass

from app.domain.catalog import BY_ID, CORE_CHORDS
from app.domain.chord import ChordNode
from app.domain.theory import Key
from app.engine.connection_engine import find_connections, score_connection
from app.style.profile import MAX_ORDER, numeral, realize, token_of

ENGINE_CANDIDATES = 24


def distribution(profile: dict, context: list[str]) -> dict[str, float]:
    """P(next token | last tokens), interpolated from order 0 up to the context length."""
    unigrams: dict[str, int] = profile.get("unigrams", {})
    total = sum(unigrams.values())
    if not total:
        return {}
    probabilities = {token: count / total for token, count in unigrams.items()}
    transitions = profile.get("transitions", {})
    for order in range(1, min(MAX_ORDER, len(context)) + 1):
        bucket = transitions.get("|".join(context[-order:]))
        if not bucket:
            continue
        counts: dict[str, int] = bucket["n"]
        seen = sum(counts.values())
        types = len(counts)
        probabilities = {
            token: (counts.get(token, 0) + types * probabilities.get(token, 0.0)) / (seen + types)
            for token in set(probabilities) | set(counts)
        }
    return probabilities


def _songs(count: int) -> str:
    return f"{count} canción" if count == 1 else f"{count} canciones"


def _times(count: int) -> str:
    return f"{count} vez" if count == 1 else f"{count} veces"


@dataclass(frozen=True)
class Evidence:
    context: list[str]
    count: int
    songs: int
    text: str


def evidence(profile: dict, context: list[str], token: str) -> Evidence:
    """The longest context after which the band played ``token``, in plain words."""
    transitions = profile.get("transitions", {})
    for order in range(min(MAX_ORDER, len(context)), 0, -1):
        ctx = context[-order:]
        bucket = transitions.get("|".join(ctx))
        if bucket and bucket["n"].get(token):
            count, songs = bucket["n"][token], bucket["s"].get(token, 1)
            path = " → ".join(numeral(item) for item in ctx)
            return Evidence(
                [numeral(item) for item in ctx], count, songs,
                f"Después de {path} la banda va a {numeral(token)} en {_songs(songs)} ({_times(count)}).",
            )
    usage = profile.get("usage", {}).get(token)
    total_songs = len(profile.get("songs", [])) or 1
    if usage:
        return Evidence([], usage["count"], usage["songs"], f"{numeral(token)} es un acorde de la banda: aparece en {usage['songs']} de {_songs(total_songs)}.")
    return Evidence([], 0, 0, f"La banda no usa {numeral(token)}: lo propone solo el motor armónico.")


def phrase(profile: dict, context: list[str], length: int = 3, beam: int = 4) -> list[str]:
    """Most likely continuation (beam search), avoiding repeating the same chord twice in a row."""
    beams: list[tuple[float, list[str]]] = [(1.0, [])]
    for _ in range(length):
        expanded = []
        for probability, tokens in beams:
            current = context + tokens
            options = distribution(profile, current)
            for token, p in sorted(options.items(), key=lambda item: -item[1])[:beam]:
                if current and token == current[-1]:
                    continue
                expanded.append((probability * p, tokens + [token]))
        if not expanded:
            break
        beams = sorted(expanded, key=lambda item: -item[0])[:beam]
    return beams[0][1] if beams and beams[0][1] else []


def suggest(profile: dict, history: list[ChordNode], key: Key, weight: float = 0.65, max_results: int = 24) -> dict:
    """Next chords ranked by ``weight`` × band style + (1 − weight) × harmonic engine."""
    current = history[-1]
    context = [token_of(chord, key) for chord in history][-MAX_ORDER:]
    probabilities = distribution(profile, context)
    colors = profile.get("colors", {})

    candidates: dict[str, ChordNode] = {}
    for token in probabilities:
        chord = BY_ID.get(realize(token, key, colors))
        if chord and chord.id != current.id:
            candidates.setdefault(chord.id, chord)
    for connection in find_connections(current, CORE_CHORDS, key.id, max_results=ENGINE_CANDIDATES):
        candidates.setdefault(connection.target.id, connection.target)

    top = max(probabilities.values(), default=0.0) or 1.0
    results = []
    for chord in candidates.values():
        token = token_of(chord, key)
        if token == context[-1]:
            continue  # Same chord in another colour is not a move.
        engine = score_connection(current, chord, key.id)
        probability = probabilities.get(token, 0.0)
        style_score = round(100 * probability / top, 1)
        proof = evidence(profile, context, token)
        results.append({
            "target": chord.id,
            "score": round(weight * style_score + (1 - weight) * engine.total, 1),
            "category": engine.category,
            "breakdown": {
                item.name: {"raw": item.raw_score, "weighted": round(item.weighted_score, 1), "detail": item.details}
                for item in engine.breakdown
            },
            "engineScore": engine.total,
            "style": {
                "score": style_score,
                "probability": round(probability, 4),
                "numeral": numeral(token),
                "context": proof.context,
                "count": proof.count,
                "songs": proof.songs,
                "evidence": proof.text,
            },
        })
    results.sort(key=lambda item: (-item["score"], item["target"]))
    # One suggestion per degree: F and Fmaj7 are the same move (♭VI), keep the best-scored colour.
    unique: dict[str, dict] = {}
    for item in results:
        unique.setdefault(item["style"]["numeral"], item)
    results = list(unique.values())

    continuation = phrase(profile, context)
    return {
        "source": current.id,
        "key": key.id,
        "context": [numeral(token) for token in context],
        "connections": results[:max_results],
        "phrase": [{"chord": realize(token, key, colors), "numeral": numeral(token)} for token in continuation],
    }
