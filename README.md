# ChordWeaver API

Backend FastAPI de ChordWeaver (Tejedor de Acordes). No es un cancionero: recibe los acordes de una canción y explica **por qué funciona** — tonalidad, grados romanos, función armónica, tensión entre acordes y sustituciones — y recomienda **qué acorde puede seguir**.

## Arranque rápido

```bash
make install        # crea .venv, instala dependencias y copia .env.example a .env
make dev            # http://localhost:8000
```

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Salud: `http://localhost:8000/health` → `{"status": "ok", "accounts": true, "version": "0.3.0"}`

Con Docker:

```bash
make docker   # lee FIREBASE_PROJECT_ID y FIREBASE_SERVICE_ACCOUNT de tu shell o de .env
```

`make help` lista todas las tareas: `test`, `lint`, `format` y `check` (lo mismo que la CI).

## Configuración

Todas las variables están documentadas en [`.env.example`](.env.example).

| Variable | Por defecto | Notas |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `development`, `test` o `production`. |
| `LOG_LEVEL` | `INFO` | Nivel de logging. |
| `FIREBASE_PROJECT_ID` | vacío | **Obligatoria para cuentas.** ID del proyecto de Firebase: verifica los tokens y abre Firestore. Vacía: cuentas y progresiones responden 503 y `/health` devuelve `accounts: false`. |
| `FIREBASE_SERVICE_ACCOUNT` | vacío | **Secreta.** Llave de una cuenta de servicio para Firestore: el JSON en una línea o en base64. Vacía: usa *Application Default Credentials* (`GOOGLE_APPLICATION_CREDENTIALS` o la identidad de Google Cloud). |
| `FIRESTORE_DATABASE` | `(default)` | Nombre de la base de Firestore. |
| `FIRESTORE_COLLECTION_PREFIX` | `chordweaver_` | Prefijo de las colecciones, para compartir un proyecto de Firebase con otras apps sin tocar sus datos. |
| `CORS_ORIGINS` | localhost:3000, 127.0.0.1:3000 y GitHub Pages | Lista separada por comas. |
| `FIREBASE_AUTH_EMULATOR_HOST` / `FIRESTORE_EMULATOR_HOST` | vacío | Emuladores locales (solo desarrollo; el de Auth se ignora en producción). |
| `WEB_URL` | GitHub Pages de la web | Destino de los enlaces para compartir (`/p/{id}`). |
| `SENTRY_DSN` | vacío | DSN del proyecto de Sentry para monitorear errores. Vacío lo desactiva. No envía datos personales. |
| `MONITORING_TEST_TOKEN` | vacío | Secreto para `GET /api/v1/monitoring/test` (cabecera `X-Test-Token`), que lanza un error a propósito para comprobar Sentry. |
| `BILLING_PROVIDER` | `mock` | Procesador de pagos. `mock` activa el plan al instante y no cobra nada (ver [Planes y suscripciones](#planes-y-suscripciones)). |

## Autenticación (Firebase)

El registro, el inicio de sesión (email y contraseña o Google), la verificación de correo y la recuperación de contraseña ocurren en **Firebase Authentication**, desde el frontend. La API recibe el **ID token** de Firebase en `Authorization: Bearer <token>` y lo verifica en [`app/core/firebase.py`](app/core/firebase.py) con las llaves públicas de Google (en caché según su `Cache-Control`): firma RS256, `aud` igual al proyecto, `iss` igual a `https://securetoken.google.com/<proyecto>`, vigencia y `sub`. No necesita *service account* ni `firebase-admin`.

- La primera petición autenticada crea el usuario en Firestore (`users/{uid}`), identificado por su UID de Firebase.
- El nombre del proveedor (por ejemplo, Google) solo se usa para crear el perfil; después el usuario puede cambiarlo o borrarlo (`PATCH /api/v1/auth/me`).
- `DELETE /api/v1/auth/me` borra los datos del usuario (y sus progresiones). La cuenta de Firebase la borra el cliente.

### Configurar Firebase

1. Crea un proyecto en <https://console.firebase.google.com> y registra una **app web**.
2. En **Authentication → Sign-in method** activa **Correo electrónico/contraseña** y **Google**.
3. En **Authentication → Settings → Authorized domains** agrega `localhost` y el dominio del frontend (por ejemplo `samuelcastillogt.github.io`).
4. Copia el **Project ID** a `FIREBASE_PROJECT_ID` en la API. La configuración web (apiKey, authDomain…) va en el frontend.
5. En **Firestore Database** crea la base (modo producción) y elige la región.
6. En **Project settings → Service accounts → Generate new private key** descarga la llave y pégala en `FIREBASE_SERVICE_ACCOUNT` (JSON en una línea o `base64 -i llave.json | tr -d '\n'`). Nunca la subas al repositorio.
7. Agrega a las reglas de Firestore (consola → Firestore → Reglas) los bloques de [`firestore.rules`](firestore.rules), que niegan el acceso directo a las colecciones de ChordWeaver. **Si el proyecto lo comparte otra app, no despliegues ese archivo**: reemplazaría todas sus reglas. Copia solo los dos bloques `match` dentro de las reglas existentes.

## Base de datos (Firestore)

Solo la API lee y escribe en Firestore, con la cuenta de servicio, que no está sujeta a las reglas. Por eso [`firestore.rules`](firestore.rules) **niega el acceso directo** a las colecciones de ChordWeaver desde navegadores y apps.

| Colección | Documento | Campos |
| --- | --- | --- |
| `chordweaver_users` | UID de Firebase | `email`, `displayName`, `photoUrl`, `createdAt`, `lastLoginAt` |
| `chordweaver_progressions` | id automático | `ownerId`, `name`, `chords`, `tonality`, `isPublic`, `source`, `createdAt`, `updatedAt` |

El prefijo (`FIRESTORE_COLLECTION_PREFIX`) permite que ChordWeaver viva en un proyecto de Firebase que ya usa otra app sin chocar con sus colecciones (por ejemplo, su propia `users`).

Las rutas no conocen Firestore: dependen de la interfaz `Repository` ([`app/repositories/base.py`](app/repositories/base.py)). [`firestore.py`](app/repositories/firestore.py) es la implementación real; [`memory.py`](app/repositories/memory.py) la usan los tests. La biblioteca de cada usuario se ordena en Python, así que no hace falta crear índices compuestos.

Para desarrollar sin tocar el proyecto real: `npx firebase-tools emulators:start --only auth,firestore --project demo-chordweaver` (el emulador de Firestore necesita Java) y en `.env` define `FIREBASE_PROJECT_ID=demo-chordweaver`, `FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099` y `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080`.

### Despliegue en Vercel

La API pública vive en `https://chords-api-python.vercel.app`. Variables a definir en el proyecto de Vercel:

1. `FIREBASE_PROJECT_ID`: el ID de tu proyecto de Firebase.
2. `FIREBASE_SERVICE_ACCOUNT`: la llave de la cuenta de servicio (márcala como *Sensitive*).
3. `CORS_ORIGINS`: debe incluir el dominio del frontend (`https://samuelcastillogt.github.io`).
4. `ENVIRONMENT=production`.

Sin Firestore configurado, la API sigue funcionando (acordes, análisis, exploración, tablatura y estilo), pero cuentas y progresiones responden 503.

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
| POST | `/api/v1/style/parse` | – | Lee una canción (acordes sobre letra, ChordPro o tablatura ASCII) y devuelve acordes, secciones y tonalidad. |
| POST | `/api/v1/style/learn` | – | Aprende el perfil de estilo de una banda a partir de sus canciones. |
| POST | `/api/v1/style/suggest` | – | Siguientes acordes mezclando el estilo de la banda con el motor armónico. |
| GET | `/api/v1/auth/me` | Bearer | Usuario de la sesión (lo crea en la primera llamada). |
| PATCH / DELETE | `/api/v1/auth/me` | Bearer | Cambia el nombre visible / borra los datos del usuario. |
| GET/POST | `/api/v1/progressions` | Bearer | Biblioteca del usuario. |
| GET | `/api/v1/progressions/{id}` | opcional | El dueño o cualquiera si `isPublic` es `true`. |
| PUT/DELETE | `/api/v1/progressions/{id}` | Bearer | Solo el dueño. `PUT {"isPublic": true}` la comparte. |
| POST | `/api/v1/feedback` | opcional | Opinión de testers y usuarios: `message`, `rating` (1–5), `email`, `page`, `source` (`web`/`app`). Se guarda en `chordweaver_feedback`. |
| GET | `/p/{id}` | – | Enlace para compartir: HTML con vista previa (Open Graph) de una progresión pública que redirige al explorador de la web. |
| GET | `/api/v1/plans` | – | Planes y precios (USD, con precio para Latinoamérica). `provider: "mock"` mientras los pagos son simulados. |
| GET | `/api/v1/billing/subscription` | Bearer | Plan del usuario, renovación y uso (`saved` / `saveLimit`). |
| POST | `/api/v1/billing/checkout` | Bearer | `{"plan": "pro", "period": "yearly", "region": "latam"}`. Con `mock` activa el plan; con un procesador real devolverá `checkoutUrl`. |
| POST | `/api/v1/billing/cancel` | Bearer | Vuelve al plan Gratis; las progresiones guardadas se conservan. |

## Planes y suscripciones

| Plan | Precio | Progresiones guardadas |
| --- | --- | --- |
| Gratis | – | 5 (al llegar al límite, `POST /progressions` responde **402**) |
| Pro | USD 4,99/mes o 29,99/año (19,99/año en Latinoamérica) | Sin límite |
| Vitalicio fundador | USD 69 en un pago (39 en Latinoamérica) | Sin límite |

Los planes y precios viven en `app/domain/plans.py`; la web los lee de `/api/v1/plans`. El plan se guarda en el usuario (`plan`, `planPeriod`, `planProvider`, `planStartedAt`, `planRenewsAt`).

**Pagos simulados (`BILLING_PROVIDER=mock`).** El checkout activa el plan sin cobrar y lo marca con `planProvider: "mock"`, para probar el flujo completo antes de tener procesador. Para conectar uno real (Paddle, Lemon Squeezy, Recurrente):

1. Implementa `BillingProvider` en `app/billing/` con `start_checkout` devolviendo la URL de pago del procesador (con el uid del usuario en los metadatos).
2. Agrega una ruta de webhook que verifique la firma del procesador y llame a `activate_plan` o `cancel_plan`.
3. Registra el proveedor en `PROVIDERS`, amplía `billing_provider` en `config.py` y cambia `BILLING_PROVIDER`.
4. Antes de cobrar, decide qué hacer con las suscripciones `mock` (pasarlas a `free` o regalarlas a los primeros testers).

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
├── main.py                 # FastAPI, CORS, logging, lifespan, /health
├── core/config.py          # Settings (env): Firebase, Firestore, CORS
├── core/firebase.py        # Verificación de ID tokens de Firebase (llaves públicas de Google)
├── core/security.py        # Dependencias de usuario y vinculación de cuentas
├── repositories/           # Interfaz Repository, Firestore y memoria (tests)
├── billing/                # Proveedores de pago (mock por ahora), activar y cancelar planes
├── domain/                 # Teoría musical: acordes, catálogo, tonalidades; plans.py: planes y precios
├── engine/                 # Motor de conexiones (7 criterios)
├── style/                  # Lectura de cifrados/tablaturas y modelo de estilo de banda
└── api/                    # Routers y esquemas Pydantic
firestore.rules             # Bloquea el acceso directo de clientes a Firestore
tests/                      # pytest (tokens firmados con una llave de prueba, Firestore falso)
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
- La tablatura usa formas comunes y, para acordes poco frecuentes, una disposición compacta generada.

## Calidad

```bash
make check   # ruff (lint + formato) y pytest con cobertura
```

Los tests cubren el parser, la detección de tonalidad, los grados, el motor, el estilo de banda, la configuración, la verificación de tokens el repositorio de Firestore (con un cliente falso que reproduce la interfaz usada) y la API completa (incluye la privacidad de progresiones entre usuarios). Los tokens de Firebase se firman con una llave RSA de prueba, así que la verificación se ejercita de verdad sin red. La CI (`.github/workflows/ci.yml`) ejecuta lint y tests en cada push.
