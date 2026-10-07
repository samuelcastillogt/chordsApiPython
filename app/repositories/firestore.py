"""Firestore repository.

Collections (names carry FIRESTORE_COLLECTION_PREFIX, "chordweaver_" by default, so the app
can live in a Firebase project shared with other apps):
- ``<prefix>users/{uid}``: email, displayName, photoUrl, createdAt, lastLoginAt (id = Firebase uid).
- ``<prefix>progressions/{id}``: ownerId, name, chords, tonality, isPublic, source, createdAt, updatedAt.

Only the API reads and writes (with a service account, which bypasses security rules), so
`firestore.rules` denies direct client access to these collections. Listing sorts in Python: a user's library
is small and this avoids having to deploy a composite index.
"""

from dataclasses import replace
from typing import Any

from google.cloud.firestore import AsyncClient
from google.cloud.firestore_v1.base_query import FieldFilter

from app.repositories.base import ProgressionRecord, UserRecord, utcnow

BATCH_LIMIT = 400  # Firestore allows 500 writes per batch.


def _user_to_doc(user: UserRecord) -> dict[str, Any]:
    return {
        "email": user.email,
        "displayName": user.display_name,
        "photoUrl": user.photo_url,
        "createdAt": user.created_at,
        "lastLoginAt": user.last_login_at,
    }


def _user_from_doc(user_id: str, data: dict[str, Any]) -> UserRecord:
    return UserRecord(
        id=user_id,
        email=data.get("email"),
        display_name=data.get("displayName"),
        photo_url=data.get("photoUrl"),
        created_at=data.get("createdAt") or utcnow(),
        last_login_at=data.get("lastLoginAt"),
    )


def _progression_to_doc(progression: ProgressionRecord) -> dict[str, Any]:
    return {
        "ownerId": progression.owner_id,
        "name": progression.name,
        "chords": list(progression.chords),
        "tonality": progression.tonality,
        "isPublic": progression.is_public,
        "source": progression.source,
        "createdAt": progression.created_at,
        "updatedAt": progression.updated_at,
    }


def _progression_from_doc(progression_id: str, data: dict[str, Any]) -> ProgressionRecord:
    return ProgressionRecord(
        id=progression_id,
        owner_id=data["ownerId"],
        name=data["name"],
        chords=list(data.get("chords") or []),
        tonality=data.get("tonality"),
        is_public=bool(data.get("isPublic")),
        source=data.get("source"),
        created_at=data.get("createdAt") or utcnow(),
        updated_at=data.get("updatedAt") or utcnow(),
    )


class FirestoreRepository:
    def __init__(self, client: AsyncClient, prefix: str = "") -> None:
        self.client = client
        self.users = f"{prefix}users"
        self.progressions = f"{prefix}progressions"

    async def get_user(self, user_id: str) -> UserRecord | None:
        snapshot = await self.client.collection(self.users).document(user_id).get()
        return _user_from_doc(snapshot.id, snapshot.to_dict() or {}) if snapshot.exists else None

    async def save_user(self, user: UserRecord) -> None:
        await self.client.collection(self.users).document(user.id).set(_user_to_doc(user))

    async def delete_user(self, user_id: str) -> None:
        refs = [snapshot.reference async for snapshot in self._owned(user_id).stream()]
        refs.append(self.client.collection(self.users).document(user_id))
        for start in range(0, len(refs), BATCH_LIMIT):
            batch = self.client.batch()
            for ref in refs[start : start + BATCH_LIMIT]:
                batch.delete(ref)
            await batch.commit()

    async def list_progressions(self, owner_id: str) -> list[ProgressionRecord]:
        progressions = [_progression_from_doc(snapshot.id, snapshot.to_dict() or {}) async for snapshot in self._owned(owner_id).stream()]
        return sorted(progressions, key=lambda item: item.updated_at, reverse=True)

    async def get_progression(self, progression_id: str) -> ProgressionRecord | None:
        snapshot = await self.client.collection(self.progressions).document(progression_id).get()
        return _progression_from_doc(snapshot.id, snapshot.to_dict() or {}) if snapshot.exists else None

    async def create_progression(self, progression: ProgressionRecord) -> ProgressionRecord:
        now = utcnow()
        ref = self.client.collection(self.progressions).document()
        created = replace(progression, id=ref.id, created_at=now, updated_at=now)
        await ref.set(_progression_to_doc(created))
        return created

    async def update_progression(self, progression: ProgressionRecord) -> ProgressionRecord:
        updated = replace(progression, updated_at=utcnow())
        await self.client.collection(self.progressions).document(updated.id).set(_progression_to_doc(updated))
        return updated

    async def delete_progression(self, progression_id: str) -> None:
        await self.client.collection(self.progressions).document(progression_id).delete()

    def _owned(self, owner_id: str):
        return self.client.collection(self.progressions).where(filter=FieldFilter("ownerId", "==", owner_id))
