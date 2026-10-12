from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


ChordSymbol = Annotated[str, Field(min_length=1, max_length=32)]
ProfileToken = Annotated[str, Field(min_length=1, max_length=32)]
NonNegativeInt = Annotated[int, Field(ge=0)]
NonBlankName = Annotated[str, Field(min_length=1, max_length=120), AfterValidator(_not_blank)]
Intent = Literal["safe", "interesting", "bold"]
ColorCounts = Annotated[
    dict[Annotated[str, Field(min_length=1, max_length=32)], NonNegativeInt],
    Field(max_length=32),
]


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
    detail: str = Field(max_length=500)


class ConnectionResponse(BaseModel):
    source: ChordSymbol
    target: str
    score: float
    intent: Intent
    category: str
    explanation: str = Field(max_length=1000)
    breakdown: dict[Annotated[str, Field(max_length=40)], CriterionResponse] = Field(max_length=16)


class ConnectionsResponse(BaseModel):
    contractVersion: Literal["1"]
    source: str
    connections: list[ConnectionResponse]
    total: int


class ParseRequest(BaseModel):
    symbols: list[ChordSymbol] = Field(min_length=1, max_length=256)


class ParsedChordResponse(BaseModel):
    input: str
    chord: str | None
    bass: str | None = None
    approximated: bool = False
    error: str | None = None


class ParseResponse(BaseModel):
    results: list[ParsedChordResponse]


class ProgressionCreateRequest(BaseModel):
    name: NonBlankName
    chords: list[ChordSymbol] = Field(min_length=1, max_length=64)
    tonality: str | None = Field(default=None, max_length=8)
    isPublic: bool = False
    source: str | None = Field(default=None, max_length=200)


class ProgressionUpdateRequest(BaseModel):
    name: NonBlankName | None = None
    chords: list[ChordSymbol] | None = Field(default=None, min_length=1, max_length=64)
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
    chords: list[ChordSymbol] = Field(min_length=2, max_length=64)
    tonality: str | None = Field(default=None, max_length=8)


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
    intent: Intent
    category: str
    explanation: str
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
    currentChord: ChordSymbol
    tonality: str | None = Field(default=None, max_length=8)
    preferredTension: str | None = Field(
        default=None,
        pattern="^(natural|medium|media|tense|tensa|extreme|extrema)$",
    )
    maxResults: int = Field(default=12, ge=1, le=72)


class SuggestionResponse(BaseModel):
    source: ChordSymbol
    target: ChordSymbol
    chord: str
    score: float
    intent: Intent
    category: str
    explanation: str
    breakdown: dict[str, CriterionResponse]


class ExploreResponse(BaseModel):
    contractVersion: Literal["1"]
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


class FeedbackRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)
    email: str | None = Field(default=None, max_length=200)
    page: str | None = Field(default=None, max_length=200)
    source: Literal["web", "app"] = "web"
    # Honeypot: hidden in the form, only bots fill it.
    website: str | None = Field(default=None, max_length=200)


class FeedbackResponse(BaseModel):
    id: str
    received: bool


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
    text: str = Field(min_length=1, max_length=20000)
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
    text: str = Field(min_length=1, max_length=20000)
    title: str | None = Field(default=None, max_length=120)
    key: str | None = Field(default=None, max_length=8)


class StyleLearnRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=80), AfterValidator(_not_blank)]
    songs: list[StyleSongInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def limit_total_text(self) -> "StyleLearnRequest":
        if sum(len(song.text) for song in self.songs) > 200000:
            raise ValueError("song text exceeds the 200000 character aggregate limit")
        return self


class StyleTransitionBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: dict[ProfileToken, NonNegativeInt] = Field(max_length=256)
    s: dict[ProfileToken, NonNegativeInt] = Field(max_length=256)


class StyleUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: NonNegativeInt
    songs: NonNegativeInt
    role: str = Field(min_length=1, max_length=32)
    numeral: str = Field(min_length=1, max_length=16)


class StyleSong(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=120)
    key: str = Field(min_length=1, max_length=8)
    keyLabel: str = Field(min_length=1, max_length=80)
    chords: list[ChordSymbol] = Field(min_length=2, max_length=2048)


class StylePattern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tokens: list[ProfileToken] = Field(min_length=3, max_length=6)
    numerals: list[Annotated[str, Field(min_length=1, max_length=16)]] = Field(min_length=3, max_length=6)
    count: NonNegativeInt
    songs: NonNegativeInt
    loop: bool


class StyleProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    name: Annotated[str, Field(min_length=1, max_length=80), AfterValidator(_not_blank)]
    songs: list[StyleSong] = Field(min_length=1, max_length=20)
    modes: dict[Annotated[str, Field(min_length=1, max_length=16)], NonNegativeInt] = Field(max_length=8)
    unigrams: dict[ProfileToken, NonNegativeInt] = Field(max_length=256)
    transitions: dict[Annotated[str, Field(min_length=1, max_length=128)], StyleTransitionBucket] = Field(max_length=8192)
    colors: dict[ProfileToken, ColorCounts] = Field(max_length=256)
    usage: dict[ProfileToken, StyleUsage] = Field(max_length=256)
    starts: dict[ProfileToken, NonNegativeInt] = Field(max_length=256)
    endings: dict[Annotated[str, Field(min_length=1, max_length=64)], NonNegativeInt] = Field(max_length=4096)
    patterns: list[StylePattern] = Field(max_length=12)
    traits: list[Annotated[str, Field(max_length=500)]] = Field(max_length=32)

    @model_validator(mode="after")
    def limit_aggregate_entries(self) -> "StyleProfile":
        transition_entries = sum(len(bucket.n) + len(bucket.s) for bucket in self.transitions.values())
        color_entries = sum(len(counts) for counts in self.colors.values())
        total_entries = (
            len(self.unigrams)
            + len(self.transitions)
            + transition_entries
            + len(self.colors)
            + color_entries
            + len(self.usage)
            + len(self.starts)
            + len(self.endings)
        )
        if total_entries > 50000:
            raise ValueError("profile exceeds the 50000 aggregate entry limit")
        return self


class StyleProfileResponse(StyleProfile):
    skipped: list[Annotated[str, Field(max_length=120)]] = Field(default_factory=list, max_length=20)


class StyleSuggestRequest(BaseModel):
    profile: StyleProfileResponse
    history: list[ChordSymbol] = Field(min_length=1, max_length=64)
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
    contractVersion: Literal["1"]
    source: str
    key: str
    context: list[str]
    connections: list[StyleConnectionResponse]
    phrase: list[StylePhraseStep]
