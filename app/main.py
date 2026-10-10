import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, auth, billing, chords, explore, feedback, progressions, share, style, tablature
from app.core.config import settings
from app.core.monitoring import init_monitoring
from app.repositories import Repository, optional_repository, repository_available

logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("chordweaver")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.auth_enabled:
        logger.warning("FIREBASE_PROJECT_ID is not set: accounts and saved progressions are disabled")
    if settings.uses_auth_emulator:
        logger.warning("Accepting unsigned tokens from the Firebase Auth emulator at %s", settings.firebase_auth_emulator_host)
    elif settings.firebase_auth_emulator_host:
        logger.warning("FIREBASE_AUTH_EMULATOR_HOST is ignored in production")
    if settings.auth_enabled:
        repository_available(log=True)
    yield


VERSION = "0.4.0"
init_monitoring(VERSION)

app = FastAPI(
    title="ChordWeaver API",
    description="Motor de conexión armónica: explica por qué funciona una progresión y qué acorde puede seguir.",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(chords.router, prefix=API_PREFIX, tags=["chords"])
app.include_router(progressions.router, prefix=API_PREFIX, tags=["progressions"])
app.include_router(explore.router, prefix=API_PREFIX, tags=["explore"])
app.include_router(analyze.router, prefix=API_PREFIX, tags=["analyze"])
app.include_router(auth.router, prefix=API_PREFIX, tags=["auth"])
app.include_router(billing.router, prefix=API_PREFIX, tags=["billing"])
app.include_router(feedback.router, prefix=API_PREFIX, tags=["feedback"])
app.include_router(share.router)
app.include_router(tablature.router, prefix=API_PREFIX, tags=["tablature"])
app.include_router(style.router, prefix=API_PREFIX, tags=["style"])


@app.get("/health", tags=["health"])
async def health_check(repository: Repository | None = Depends(optional_repository)):
    accounts = settings.auth_enabled and repository is not None
    return {"status": "ok", "accounts": accounts, "billing": settings.billing_provider, "version": app.version}


@app.get(f"{API_PREFIX}/monitoring/test", include_in_schema=False)
async def monitoring_test(x_test_token: str = Header(default="")):
    """Raises an error on purpose so you can check it reaches Sentry. Needs MONITORING_TEST_TOKEN."""
    if not settings.monitoring_test_token or x_test_token != settings.monitoring_test_token:
        raise HTTPException(status_code=404, detail="Not Found")
    raise RuntimeError("Prueba de monitoreo de ChordWeaver API")
