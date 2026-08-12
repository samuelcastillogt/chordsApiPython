from dataclasses import dataclass, field

from app.domain.chord import ChordNode


@dataclass
class CriterionScore:
    name: str
    weight: float
    raw_score: float
    weighted_score: float
    details: str = ""


@dataclass
class ConnectionScore:
    source: ChordNode
    target: ChordNode
    total: float
    category: str
    breakdown: list[CriterionScore] = field(default_factory=list)
