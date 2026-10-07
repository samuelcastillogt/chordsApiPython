from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    StyleLearnRequest,
    StyleParseRequest,
    StyleParseResponse,
    StyleProfileResponse,
    StyleSuggestRequest,
    StyleSuggestResponse,
)
from app.domain.catalog import find_chord
from app.domain.theory import detect_key, parse_key
from app.style.model import suggest
from app.style.profile import learn_profile, tokenize_song
from app.style.sheet_parser import parse_song

router = APIRouter()


@router.post("/style/parse", response_model=StyleParseResponse)
async def parse_song_text(request: StyleParseRequest):
    """Reads one song (chords over lyrics, ChordPro or ASCII tab) and returns its chords and key."""
    song = parse_song(request.text, request.title or "Canción")
    chords = song.chords
    key = parse_key(request.key) or (detect_key(chords).key if chords else None)
    return {
        "title": song.title,
        "chords": [chord.id for chord in chords],
        "sections": [{"name": section.name, "chords": [chord.id for chord in section.chords]} for section in song.sections],
        "key": key.id if key else None,
        "keyLabel": key.label if key else None,
        "tabChords": song.tab_chords,
        "unknown": song.unknown,
    }


@router.post("/style/learn", response_model=StyleProfileResponse)
async def learn_style(request: StyleLearnRequest):
    """Learns a band profile from its songs: transitions, signature chords and recurring patterns."""
    songs = []
    skipped = []
    for index, item in enumerate(request.songs):
        tokens = tokenize_song(parse_song(item.text, item.title or f"Canción {index + 1}"), item.key)
        if tokens:
            songs.append(tokens)
        else:
            skipped.append(item.title or f"Canción {index + 1}")
    if not songs:
        raise HTTPException(
            status_code=422, detail="No se encontraron acordes en ninguna canción. Pega cifrados o tablaturas con al menos dos acordes."
        )
    return {**learn_profile(request.name.strip(), songs), "skipped": skipped}


@router.post("/style/suggest", response_model=StyleSuggestResponse)
async def suggest_in_style(request: StyleSuggestRequest):
    """Next chords after ``history`` blending the band's habits with the harmonic engine."""
    history = [find_chord(symbol) for symbol in request.history]
    key = parse_key(request.tonality) or detect_key(history).key
    return suggest(request.profile.model_dump(), history, key, request.weight, request.maxResults)
