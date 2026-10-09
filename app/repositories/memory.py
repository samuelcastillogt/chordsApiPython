"""In-memory repository: used by the tests (and handy for trying the API without a database)."""

from dataclasses import replace
from uuid import uuid4

from app.repositories.base import ProgressionRecord, UserRecord, utcnow


class InMemoryRepository:
    def __init__(self) -> None:
        self.users: dict[str, UserRecord] = {}
        self.progressions: dict[str, ProgressionRecord] = {}

    async def get_user(self, user_id: str) -> UserRecord | None:
        user = self.users.get(user_id)
        return replace(user) if user else None

    async def save_user(self, user: UserRecord) -> None:
        self.users[user.id] = replace(user)

    async def delete_user(self, user_id: str) -> None:
        self.users.pop(user_id, None)
        for progression_id in [pid for pid, item in self.progressions.items() if item.owner_id == user_id]:
            del self.progressions[progression_id]

    async def list_progressions(self, owner_id: str) -> list[ProgressionRecord]:
        owned = [replace(item) for item in self.progressions.values() if item.owner_id == owner_id]
        return sorted(owned, key=lambda item: item.updated_at, reverse=True)

    async def count_progressions(self, owner_id: str) -> int:
        return sum(1 for item in self.progressions.values() if item.owner_id == owner_id)

    async def get_progression(self, progression_id: str) -> ProgressionRecord | None:
        progression = self.progressions.get(progression_id)
        return replace(progression) if progression else None

    async def create_progression(self, progression: ProgressionRecord) -> ProgressionRecord:
        now = utcnow()
        created = replace(progression, id=uuid4().hex, created_at=now, updated_at=now)
        self.progressions[created.id] = created
        return replace(created)

    async def update_progression(self, progression: ProgressionRecord) -> ProgressionRecord:
        updated = replace(progression, updated_at=utcnow())
        self.progressions[updated.id] = updated
        return replace(updated)

    async def delete_progression(self, progression_id: str) -> None:
        self.progressions.pop(progression_id, None)
