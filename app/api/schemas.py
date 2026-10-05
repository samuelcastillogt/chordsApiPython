from pydantic import BaseModel, Field


class ChordResponse(BaseModel):
    id: str
    root: str
    type: str
    triad: list[str]
    circlePosition: int


class CriterionResponse(BaseModel):
    raw: float
    weighted: float
    detail: str


class ConnectionResponse(BaseModel):
    target: str
    score: float
    category: str
    breakdown: dict[str, CriterionResponse]


class ConnectionsResponse(BaseModel):
    source: str
    connections: list[ConnectionResponse]
    total: int


class ProgressionCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    chords: list[str] = Field(min_length=1)
    tonality: str | None = None


class ProgressionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    chords: list[str] | None = Field(default=None, min_length=1)
    tonality: str | None = None


class ProgressionResponse(BaseModel):
    id: str
    name: str
    chords: list[str]
    tonality: str | None
    createdAt: str
    updatedAt: str


class ProgressionListResponse(BaseModel):
    progressions: list[ProgressionResponse]
    total: int


class AnalyzeRequest(BaseModel):
    chords: list[str] = Field(min_length=2)
    tonality: str | None = None


class ProgressionConnectionResponse(BaseModel):
    source: str
    target: str
    score: float
    category: str
    breakdown: dict[str, CriterionResponse]


class AnalyzeResponse(BaseModel):
    analysis: dict


class TablatureRequest(BaseModel):
    chords: list[str] = Field(min_length=1)
    title: str | None = None


class TablatureChordResponse(BaseModel):
    chord: str
    frets: list[str]


class TablatureResponse(BaseModel):
    title: str
    tuning: list[str]
    chords: list[str]
    lines: list[str]
    arpeggioLines: list[str]
    text: str
    diagrams: list[TablatureChordResponse]


class ExploreRequest(BaseModel):
    currentChord: str
    tonality: str | None = None
    preferredTension: str | None = Field(
        default=None,
        pattern="^(natural|medium|media|tense|tensa|extreme|extrema)$",
    )
    maxResults: int = Field(default=12, ge=1, le=72)


class SuggestionResponse(BaseModel):
    chord: str
    score: float
    category: str
    explanation: str


class ExploreResponse(BaseModel):
    currentChord: str
    suggestions: list[SuggestionResponse]
    total: int


class AuthRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
