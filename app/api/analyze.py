from fastapi import APIRouter, HTTPException

from app.api.explore import serialize_connection
from app.api.schemas import AnalyzeRequest, AnalyzeResponse
from app.domain.catalog import BY_ID, parse
from app.domain.chord import ChordParseError
from app.domain.theory import analyze_chord, detect_key, parse_key, suggest_substitutions
from app.engine.connection_engine import score_connection

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, response_model_by_alias=True)
async def analyze_progression(request: AnalyzeRequest):
    """Explains a progression: key, roman numerals, functions, tension and substitutions."""
    try:
        parsed = [parse(symbol) for symbol in request.chords]
    except ChordParseError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    chords = [item.chord for item in parsed]

    key = parse_key(request.tonality)
    detected = key is None
    confidence = 1.0
    if key is None:
        guess = detect_key(chords)
        key, confidence = guess.key, guess.confidence
    tonality = key.id

    degrees = []
    for item in parsed:
        result = analyze_chord(item.chord, key)
        degrees.append({
            "input": item.input,
            "chord": item.chord.id,
            "numeral": result.numeral,
            "function": result.function,
            "role": result.role,
            "explanation": result.explanation,
            "approximated": item.approximated,
            "substitutions": [vars(sub) for sub in suggest_substitutions(item.chord, key, BY_ID)],
        })

    connections = []
    tension_curve = []
    for source, target in zip(chords, chords[1:]):
        connection = score_connection(source, target, tonality)
        connections.append({"source": source.id, **serialize_connection(connection)})
        tension_curve.append({"from": source.id, "to": target.id, "score": connection.total, "category": connection.category})

    average_score = round(sum(point["score"] for point in tension_curve) / len(tension_curve), 1)
    roles = [degree["role"] for degree in degrees]
    suggestions = []
    if average_score < 50:
        suggestions.append("La progresión tiene alta tensión; prueba insertar acordes puente o una dominante antes de los saltos.")
    else:
        suggestions.append("La progresión mantiene continuidad armónica estable.")
    if "secondary_dominant" in roles:
        suggestions.append("Usa dominantes secundarias: cada una empuja hacia el acorde que la sigue.")
    if "borrowed" in roles:
        suggestions.append(f"Tiene acordes prestados del modo paralelo, que dan color fuera de {key.label}.")
    if all(role == "diatonic" for role in roles):
        suggestions.append(f"Todos los acordes pertenecen a {key.label}; prueba una sustitución para sorprender.")

    return {
        "analysis": {
            "chords": [chord.id for chord in chords],
            "key": {"id": key.id, "label": key.label, "mode": key.mode, "confidence": confidence, "detected": detected},
            "degrees": degrees,
            "connections": connections,
            "tensionCurve": tension_curve,
            "averageScore": average_score,
            "suggestions": suggestions,
        }
    }
