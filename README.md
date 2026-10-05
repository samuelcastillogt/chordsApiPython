# ChordWeaver API

Backend FastAPI de ChordWeaver (Tejedor de Acordes). No es un cancionero: recibe los acordes de una canción y explica **por qué funciona** — tonalidad, grados romanos, función armónica, tensión entre acordes y sustituciones — y recomienda **qué acorde puede seguir**.

## Arranque rápido

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Salud: `http://localhost:8000/health` → `{"status": "ok", "accounts": true}`

Con Docker (API + PostgreSQL):

```bash
docker compose up --build
```

## Configuración

| Variable | Por defecto | Notas |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./chordweaver.db` | En producción usa PostgreSQL. Las URLs `postgres://` y `postgresql://` se convierten solas a `postgresql+asyncpg://`. |
| `SECRET_KEY` | `change-me-in-production` | **Obligatoria en producción.** Con el valor por defecto en Vercel/producción las cuentas quedan deshabilitadas (`/health` devuelve `accounts: false`) y los endpoints de cuentas y progresiones responden 503. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 días) | Vida del JWT. |
| `CORS_ORIGINS` | localhost:3000, 127.0.0.1:3000 y GitHub Pages | Lista separada por comas. |
| `ENVIRONMENT` | `development` | `production` activa las protecciones de producción fuera de Vercel. |

Las tablas se crean al arrancar (`create_all`). Si la base de datos no responde, la API sigue sirviendo los endpoints sin estado (acordes, exploración, análisis, tablatura) y solo cuentas/progresiones devuelven 503.

### Despliegue en Vercel

La API pública vive en `https://chords-api-python.vercel.app`. Para activar cuentas y progresiones persistentes:

1. Crea una base PostgreSQL (Neon, Supabase, Vercel Postgres…) y define `DATABASE_URL`.
2. Define `SECRET_KEY` con un valor largo y aleatorio (`python -c "import secrets; print(secrets.token_urlsafe(48))"`).
3. Revisa `CORS_ORIGINS` (debe incluir `https://samuelcastillogt.github.io`).

El runtime de Python de Vercel no incluye `sqlite3`: sin `DATABASE_URL` la API sigue funcionando (acordes, análisis, exploración, tablatura) pero cuentas y progresiones responden 503 y `/health` informa `accounts: false`. El motor de base de datos se crea de forma diferida para que un driver ausente nunca impida arrancar la app.

## Endpoints

| Método | Ruta | Auth | Descripción |
| --- | --- | --- | --- |
| GET | `/api/v1/chords` | – | Catálogo de 192 acordes (12 raíces × 16 cualidades) con `notes` y `triad`. |
| GET | `/api/v1/chords/{símbolo}` | – | Acepta cualquier cifrado: `Bb`, `SOLm`, `F#m7(b5)`… |
| POST | `/api/v1/chords/parse` | – | Normaliza una lista de símbolos y reporta los que no son acordes. |
| GET | `/api/v1/chords/{símbolo}/connections` | – | Siguientes acordes recomendados (`tonality`, `min_score`, `max_results`). |
| POST | `/api/v1/explore` | – | Igual que el anterior con filtro por tensión preferida. |
| POST | `/api/v1/analyze` | – | Análisis completo de una progresión; detecta la tonalidad si no se envía. |
| POST | `/api/v1/tablature` | – | Tablatura de texto con posiciones y arpegio sugerido. |
| POST | `/api/v1/auth/register` · `/auth/login` | – | Devuelven `{accessToken, user}`. |
| GET | `/api/v1/auth/me` | Bearer | Usuario de la sesión. |
| GET/POST | `/api/v1/progressions` | Bearer | Biblioteca del usuario. |
| GET | `/api/v1/progressions/{id}` | opcional | El dueño o cualquiera si `isPublic` es `true`. |
| PUT/DELETE | `/api/v1/progressions/{id}` | Bearer | Solo el dueño. `PUT {"isPublic": true}` la comparte. |

### Ejemplo: analizar una canción

```bash
curl -X POST localhost:8000/api/v1/analyze -H 'content-type: application/json' \
  -d '{"chords": ["Bm", "G", "D", "A"]}'
```

```jsonc
{
  "analysis": {
    "key": {"id": "Bm", "label": "Si menor (Bm)", "detected": true, "confidence": 0.61},
    "degrees": [
      {"input": "Bm", "numeral": "i",  "function": "T", "role": "diatonic", "substitutions": [...]},
      {"input": "G",  "numeral": "VI", "function": "T", ...},
      {"input": "D",  "numeral": "III","function": "T", ...},
      {"input": "A",  "numeral": "VII","function": "D", ...}
    ],
    "tensionCurve": [{"from": "Bm", "to": "G", "score": 55.8, "category": "media"}, ...],
    "averageScore": 55.8,
    "suggestions": ["..."]
  }
}
```

## Arquitectura

```
app/
├── main.py                 # FastAPI, CORS, lifespan (crea tablas)
├── core/config.py          # Settings (env), normalización de DATABASE_URL, flags de producción
├── core/security.py        # PBKDF2 (600k iteraciones), JWT, dependencias de usuario
├── db.py                   # Motor async SQLAlchemy y sesión con degradación a 503
├── models/__init__.py      # User, Progression
├── domain/chord.py         # Notas, cualidades, ChordNode y parser de cifrados
├── domain/catalog.py       # Catálogo único (ALL_CHORDS, CORE_CHORDS, BY_ID) y find_chord
├── domain/theory.py        # Tonalidades, grados, funciones, detección de tonalidad, sustituciones
├── engine/criteria.py      # Los 7 criterios de conexión
├── engine/connection_engine.py  # score_connection (con caché LRU) y find_connections
└── api/                    # Routers y esquemas Pydantic
```

## Modelo musical

### Intervalos y transposición

La escala cromática tiene 12 clases de altura (`C=0 … B=11`). Un intervalo es una cantidad de semitonos desde la raíz y la escala es circular (`% 12`):

```text
B (11) + 4 semitonos = 15 → 15 % 12 = 3 → D#
```

`transpose_note(note, semitones)` busca el índice, suma y aplica módulo. No sabe nada de acordes.

### Cualidades de acorde

Las fórmulas viven como datos en `QUALITIES` (`app/domain/chord.py`). `build_chord_notes(root, type)` aplica la fórmula a la raíz.

| Tipo | Sufijo | Fórmula | Ejemplo desde C | Familia |
| --- | --- | --- | --- | --- |
| Mayor | – | `0 4 7` | C E G | major |
| Menor | `m` | `0 3 7` | C D# G | minor |
| Disminuido | `°` | `0 3 6` | C D# F# | diminished |
| Aumentado | `+` | `0 4 8` | C E G# | augmented |
| Dominante 7 | `7` | `0 4 7 10` | C E G A# | dominant |
| Disminuido 7 | `°7` | `0 3 6 9` | C D# F# A | diminished |
| Séptima mayor | `maj7` | `0 4 7 11` | C E G B | major |
| Menor 7 | `m7` | `0 3 7 10` | C D# G A# | minor |
| Semidisminuido | `m7b5` | `0 3 6 10` | C D# F# A# | diminished |
| Sus2 / Sus4 | `sus2` / `sus4` | `0 2 7` / `0 5 7` | C D G / C F G | suspended |
| Add9 | `add9` | `0 4 7 2` | C E G D | major |
| Sexta / menor sexta | `6` / `m6` | `0 4 7 9` / `0 3 7 9` | C E G A | major / minor |
| Novena | `9` | `0 4 7 10 2` | C E G A# D | dominant |
| Power chord | `5` | `0 7` | C G | power |

`ChordNode` guarda `root`, `chord_type`, `notes` y `circle_position`; `triad` (las tres primeras notas) se mantiene por compatibilidad con clientes anteriores.

### Parser de cifrados

`parse_chord_symbol` entiende cifrado americano y latino (`DO`, `Sol#m`), bemoles (se normalizan a sostenidos: `Bb` → `A#`), acordes con bajo (`D/F#` → `D` con `bass=F#`) y paréntesis (`F#m7(b5)`). Las extensiones que el motor no modela se aproximan al acorde más cercano y se marcan con `approximated: true` (`Fmaj9` → `Fmaj7`, `E7#9` → `E7`).

### Teoría tonal (`domain/theory.py`)

- **Tonalidades**: 24 (`C`…`B`, `Cm`…`Bm`). En menor se aceptan además V, V7 y vii°7 de la menor armónica.
- **Grados romanos**: mayúsculas para familias mayores, minúsculas para menores y disminuidas, con sufijos (`V7`, `iiø7`, `bVII`, `Imaj7`).
- **Roles**: `diatonic`, `secondary_dominant` (`V7/ii` cuando un acorde dominante resuelve una quinta abajo sobre un grado diatónico), `borrowed` (pertenece al modo paralelo, p. ej. `iv` en mayor) y `chromatic`.
- **Funciones**: T (I, iii, vi), SD (ii, IV), D (V, vii°); en menor T (i, III, VI), SD (ii°, iv), D (v/V, VII, vii°).
- **Detección de tonalidad**: puntúa las 24 tonalidades según cuántos acordes encajan (diatónico 1, dominante secundaria 0,55, prestado 0,3), con bonus si el primer o último acorde es la tónica, por cadencias V→I y por patrones de blues (I7-IV7-V7). La confianza refleja la distancia con la segunda mejor tonalidad.
- **Sustituciones**: relativo, color (maj7, add9, m7), sustituto tritonal, suspensión, préstamos modales (iv, bVII) y dominante de preparación.

### Motor de conexiones

`score_connection(a, b, tonality)` combina siete criterios (0–100) con estos pesos:

| Criterio | Peso | Qué mide |
| --- | --- | --- |
| `shared_notes` | 0,25 | Notas comunes relativas al acorde más pequeño. |
| `circle_distance` | 0,15 | Distancia de las raíces en el círculo de quintas. |
| `voice_movement` | 0,15 | Menor movimiento total en semitonos al llevar las voces de un acorde al otro (funciona con acordes de 2 a 5 notas). |
| `transformation` | 0,15 | Paralelo, relativo, resolución dominante→tónica, movimiento de cuarta/quinta, tritonal, resolución de suspensión. |
| `tonal_function` | 0,15 | Flujo funcional en la tonalidad (D→T 100, SD→D 95…), penaliza acordes prestados o cromáticos. |
| `dominant_chain` | 0,10 | Resolución por quinta descendente. |
| `glue_magic` | 0,05 | Nota puente compartida que es la raíz del acorde de origen. |

Categorías: `natural` ≥ 70, `media` ≥ 50, `tensa` ≥ 30, `extrema` < 30.

`find_connections` solo recomienda cualidades principales (`CORE_TYPES`: mayor, menor, 7, maj7, m7, °, ø, °7, +) y se queda con la mejor opción por raíz y familia, para no sugerir C7, Cmaj7 y C6 como si fueran movimientos distintos. Los acordes de color aparecen como sustituciones en `/analyze`.

### Limitaciones conocidas

- Se trabaja con clases de altura: no hay octavas, inversiones ni voicings reales (el bajo de los slash chords se reporta pero no puntúa).
- La escritura es solo con sostenidos en los IDs (`A#`); las etiquetas de tonalidad sí usan bemoles (`Sib mayor (Bb)`).
- Las tablas se crean con `create_all`; si el esquema cambia, añade migraciones (Alembic) antes de tener datos reales en producción.
- La tablatura usa formas comunes y, para acordes poco frecuentes, una disposición compacta generada.

## Tests

```bash
pytest -q
```

Cubren el parser, la detección de tonalidad, los grados, el motor, la configuración y la API completa (incluye privacidad de progresiones entre usuarios). La CI (`.github/workflows/ci.yml`) los ejecuta en cada push.
