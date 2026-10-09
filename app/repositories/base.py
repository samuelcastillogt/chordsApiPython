"""Storage contract for users and progressions. Routes depend on this, never on Firestore."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class UserRecord:
    id: str  # Firebase Authentication uid
    email: str | None = None
    display_name: str | None = None
    photo_url: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    last_login_at: datetime | None = None
    # Subscription (see app/domain/plans.py and app/billing). Only the billing layer changes these.
    plan: str = "free"
    plan_period: str | None = None  # monthly | yearly | once
    plan_provider: str | None = None  # mock today; the real processor later
    plan_started_at: datetime | None = None
    plan_renews_at: datetime | None = None


@dataclass
class ProgressionRecord:
    owner_id: str
    name: str
    chords: list[str]
    tonality: str | None = None
    is_public: bool = False
    source: str | None = None
    id: str = ""  # Assigned by the repository on create.
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


class Repository(Protocol):
    async def get_user(self, user_id: str) -> UserRecord | None: ...

    async def save_user(self, user: UserRecord) -> None: ...

    async def delete_user(self, user_id: str) -> None:
        """Deletes the user and every progression they own."""

    async def list_progressions(self, owner_id: str) -> list[ProgressionRecord]:
        """The owner's progressions, most recently updated first."""

    async def count_progressions(self, owner_id: str) -> int: ...

    async def get_progression(self, progression_id: str) -> ProgressionRecord | None: ...

    async def create_progression(self, progression: ProgressionRecord) -> ProgressionRecord: ...

    async def update_progression(self, progression: ProgressionRecord) -> ProgressionRecord: ...

    async def delete_progression(self, progression_id: str) -> None: ...


class RepositoryUnavailableError(Exception):
    """The database is not configured or cannot be reached."""
