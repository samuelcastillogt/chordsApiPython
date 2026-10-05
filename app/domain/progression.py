from dataclasses import dataclass, field
from datetime import datetime

from app.domain.chord import ChordNode


@dataclass
class Progression:
    id: str | None = None
    name: str = ""
    chords: list[ChordNode] = field(default_factory=list)
    tonality: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
