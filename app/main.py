from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import analyze, auth, chords, explore, progressions, tablature

app = FastAPI(
    title="ChordWeaver API",
    description="Motor de conexión armónica visual",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chords.router, prefix="/api/v1", tags=["chords"])
app.include_router(progressions.router, prefix="/api/v1", tags=["progressions"])
app.include_router(explore.router, prefix="/api/v1", tags=["explore"])
app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(tablature.router, prefix="/api/v1", tags=["tablature"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
