# ChordWeaver Backend

FastAPI backend for the ChordWeaver harmonic connection engine.

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Swagger

After starting the server, open:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Healthcheck: `http://localhost:8000/health`

## Implemented Endpoints

- `GET /api/v1/chords`
- `GET /api/v1/chords/{id}`
- `GET /api/v1/chords/{id}/connections?tonality=C&min_score=20&max_results=12`
- `POST /api/v1/explore`
- `POST /api/v1/analyze`
- `POST /api/v1/tablature`
- `POST /api/v1/progressions`
- `GET /api/v1/progressions`
- `GET /api/v1/progressions/{id}`
- `PUT /api/v1/progressions/{id}`
- `DELETE /api/v1/progressions/{id}`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

Progressions and auth currently use in-memory repositories because the repository had no active database/session layer. The public REST contract is ready for replacing that storage with SQLAlchemy/PostgreSQL. Connection scores are cached in-process; Redis can replace this cache behind the same engine boundary.

`POST /api/v1/tablature` generates a deterministic text tablature for the submitted chord sequence using standard guitar tuning. Common open/barre shapes are used when available; uncommon generated chords fall back to a compact triad voicing. The response includes chord-position lines and a suggested arpeggio pattern that shows only string lines and note frets.

## Tests

```bash
pytest
```
