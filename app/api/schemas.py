from pydantic import BaseModel, Field


class ChordResponse(BaseModel):
    id: str
    root: str
    type: str
    family: str
    label: str
    notes: list[str]
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


class ParseRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=256)


class ParsedChordResponse(BaseModel):
    input: str
    chord: str | None
    bass: str | None = None
    approximated: bool = False
    error: str | None = None


class ParseResponse(BaseModel):
    results: list[ParsedChordResponse]


class ProgressionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    chords: list[str] = Field(min_length=1, max_length=64)
    tonality: str | None = Field(default=None, max_length=8)
    isPublic: bool = False
    source: str | None = Field(default=None, max_length=200)


class ProgressionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    chords: list[str] | None = Field(default=None, min_length=1, max_length=64)
    tonality: str | None = Field(default=None, max_length=8)
    isPublic: bool | None = None


class ProgressionResponse(BaseModel):
    id: str
    name: str
    chords: list[str]
    tonality: str | None
    isPublic: bool = False
    isOwner: bool = False
    source: str | None = None
    createdAt: str
    updatedAt: str


class ProgressionListResponse(BaseModel):
    progressions: list[ProgressionResponse]
    total: int


class AnalyzeRequest(BaseModel):
    chords: list[str] = Field(min_length=2, max_length=64)
    tonality: str | None = None


class KeyResponse(BaseModel):
    id: str
    label: str
    mode: str
    confidence: float
    detected: bool


class SubstitutionResponse(BaseModel):
    chord: str
    kind: str
    reason: str


class DegreeResponse(BaseModel):
    input: str
    chord: str
    numeral: str
    function: str | None
    role: str
    explanation: str
    approximated: bool
    substitutions: list[SubstitutionResponse]


class ProgressionConnectionResponse(BaseModel):
    source: str
    target: str
    score: float
    category: str
    breakdown: dict[str, CriterionResponse]


class TensionPointResponse(BaseModel):
    model_config = {"populate_by_name": True}

    from_: str = Field(alias="from", serialization_alias="from")
    to: str
    score: float
    category: str


class AnalysisResponse(BaseModel):
    chords: list[str]
    key: KeyResponse
    degrees: list[DegreeResponse]
    connections: list[ProgressionConnectionResponse]
    tensionCurve: list[TensionPointResponse]
    averageScore: float
    suggestions: list[str]


class AnalyzeResponse(BaseModel):
    analysis: AnalysisResponse


class TablatureRequest(BaseModel):
    chords: list[str] = Field(min_length=1, max_length=64)
    title: str | None = Field(default=None, max_length=120)


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
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    displayName: str | None = Field(default=None, max_length=80)


class UserResponse(BaseModel):
    id: str
    email: str
    displayName: str | None


class TokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    user: UserResponse
