from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.api.schemas import (
    StyleLearnRequest,
    StyleParseRequest,
    StyleParseResponse,
    StyleProfileResponse,
    StyleSuggestRequest,
    StyleSuggestResponse,
)
from app.domain.catalog import find_chord
from app.domain.theory import Key, detect_key, parse_key
from app.style.model import suggest
from app.style.profile import learn_profile, tokenize_song
from app.style.sheet_parser import parse_song

router = APIRouter()


def _explicit_key(value: str | None) -> Key | None:
    key = parse_key(value)
    if value is not None and key is None:
        raise HTTPException(status_code=400, detail=f"Unknown tonality: {value}")
    return key


def _parse_song_text(request: StyleParseRequest) -> dict:
    explicit_key = _explicit_key(request.key)
    song = parse_song(request.text, request.title or "Canción")
    chords = song.chords
    key = explicit_key or (detect_key(chords).key if chords else None)
    return {
        "title": song.title,
        "chords": [chord.id for chord in chords],
        "sections": [{"name": section.name, "chords": [chord.id for chord in section.chords]} for section in song.sections],
        "key": key.id if key else None,
        "keyLabel": key.label if key else None,
        "tabChords": song.tab_chords,
        "unknown": song.unknown,
    }


@router.post("/style/parse", response_model=StyleParseResponse)
async def parse_song_text(request: StyleParseRequest):
    """Reads one song (chords over lyrics, ChordPro or ASCII tab) and returns its chords and key."""
    return await run_in_threadpool(_parse_song_text, request)


def _learn_style(request: StyleLearnRequest) -> dict:
    songs = []
    skipped = []
    for index, item in enumerate(request.songs):
        explicit_key = _explicit_key(item.key)
        tokens = tokenize_song(parse_song(item.text, item.title or f"Canción {index + 1}"), explicit_key.id if explicit_key else None)
        if tokens:
            songs.append(tokens)
        else:
            skipped.append(item.title or f"Canción {index + 1}")
    if not songs:
        raise HTTPException(
            status_code=422, detail="No se encontraron acordes en ninguna canción. Pega cifrados o tablaturas con al menos dos acordes."
        )
    return {**learn_profile(request.name.strip(), songs), "skipped": skipped}


@router.post("/style/learn", response_model=StyleProfileResponse)
async def learn_style(request: StyleLearnRequest):
    """Learns a band profile from its songs: transitions, signature chords and recurring patterns."""
    return await run_in_threadpool(_learn_style, request)


def _suggest_in_style(request: StyleSuggestRequest) -> dict:
    history = [find_chord(symbol) for symbol in request.history]
    explicit_key = _explicit_key(request.tonality)
    key = explicit_key or detect_key(history).key
    return suggest(request.profile.model_dump(), history, key, request.weight, request.maxResults)


@router.post("/style/suggest", response_model=StyleSuggestResponse)
async def suggest_in_style(request: StyleSuggestRequest):
    """Next chords after ``history`` blending the band's habits with the harmonic engine."""
    return await run_in_threadpool(_suggest_in_style, request)
