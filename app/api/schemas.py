from typing import Literal

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


class UserResponse(BaseModel):
    id: str
    email: str | None
    displayName: str | None
    photoUrl: str | None = None
    plan: str = "free"


class PriceResponse(BaseModel):
    period: Literal["monthly", "yearly", "once"]
    amount: float
    currency: str
    region: Literal["global", "latam"]


class PlanResponse(BaseModel):
    id: str
    name: str
    tagline: str
    saveLimit: int | None
    features: list[str]
    prices: list[PriceResponse]


class PlansResponse(BaseModel):
    provider: str
    plans: list[PlanResponse]


class SubscriptionResponse(BaseModel):
    plan: str
    planName: str
    period: str | None
    provider: str | None
    startedAt: str | None
    renewsAt: str | None
    saved: int
    saveLimit: int | None


class CheckoutRequest(BaseModel):
    plan: Literal["pro", "lifetime"]
    period: Literal["monthly", "yearly", "once"]
    region: Literal["global", "latam"] = "global"


class CheckoutResponse(BaseModel):
    provider: str
    checkoutUrl: str | None
    activated: bool
    subscription: SubscriptionResponse


class UserUpdateRequest(BaseModel):
    displayName: str | None = Field(default=None, max_length=80)


class StyleParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=40000)
    title: str | None = Field(default=None, max_length=120)
    key: str | None = Field(default=None, max_length=8)


class StyleSectionResponse(BaseModel):
    name: str
    chords: list[str]


class StyleParseResponse(BaseModel):
    title: str
    chords: list[str]
    sections: list[StyleSectionResponse]
    key: str | None
    keyLabel: str | None
    tabChords: int
    unknown: list[str]


class StyleSongInput(BaseModel):
    text: str = Field(min_length=1, max_length=40000)
    title: str | None = Field(default=None, max_length=120)
    key: str | None = Field(default=None, max_length=8)


class StyleLearnRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    songs: list[StyleSongInput] = Field(min_length=1, max_length=60)


class StyleTransitionBucket(BaseModel):
    n: dict[str, int]
    s: dict[str, int]


class StyleUsage(BaseModel):
    count: int
    songs: int
    role: str
    numeral: str


class StyleSong(BaseModel):
    title: str
    key: str
    keyLabel: str
    chords: list[str]


class StylePattern(BaseModel):
    tokens: list[str]
    numerals: list[str]
    count: int
    songs: int
    loop: bool


class StyleProfile(BaseModel):
    version: int = 1
    name: str
    songs: list[StyleSong]
    modes: dict[str, int]
    unigrams: dict[str, int]
    transitions: dict[str, StyleTransitionBucket]
    colors: dict[str, dict[str, int]]
    usage: dict[str, StyleUsage]
    starts: dict[str, int]
    endings: dict[str, int]
    patterns: list[StylePattern]
    traits: list[str]


class StyleProfileResponse(StyleProfile):
    skipped: list[str] = []


class StyleSuggestRequest(BaseModel):
    profile: StyleProfile
    history: list[str] = Field(min_length=1, max_length=64)
    tonality: str | None = Field(default=None, max_length=8)
    weight: float = Field(default=0.65, ge=0, le=1)
    maxResults: int = Field(default=24, ge=1, le=72)


class StyleInfoResponse(BaseModel):
    score: float
    probability: float
    numeral: str
    context: list[str]
    count: int
    songs: int
    evidence: str


class StyleConnectionResponse(ConnectionResponse):
    engineScore: float
    style: StyleInfoResponse


class StylePhraseStep(BaseModel):
    chord: str
    numeral: str


class StyleSuggestResponse(BaseModel):
    source: str
    key: str
    context: list[str]
    connections: list[StyleConnectionResponse]
    phrase: list[StylePhraseStep]
