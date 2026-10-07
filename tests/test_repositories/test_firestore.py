import asyncio
from datetime import timedelta

from app.repositories import firestore as firestore_module
from app.repositories.base import ProgressionRecord, UserRecord, utcnow
from app.repositories.firestore import FirestoreRepository
from tests.fake_firestore import FakeFirestore


def run(coroutine):
    return asyncio.run(coroutine)


def make() -> tuple[FirestoreRepository, FakeFirestore]:
    client = FakeFirestore()
    return FirestoreRepository(client, prefix="cw_"), client  # type: ignore[arg-type]


def test_users_are_stored_by_uid_with_camel_case_fields():
    repository, client = make()
    run(repository.save_user(UserRecord(id="uid-1", email="ana@example.com", display_name="Ana")))

    stored = client.store["cw_users"]["uid-1"]
    assert stored["email"] == "ana@example.com" and stored["displayName"] == "Ana"
    user = run(repository.get_user("uid-1"))
    assert user is not None and user.display_name == "Ana"
    assert run(repository.get_user("missing")) is None


def test_progressions_round_trip_and_list_newest_first():
    repository, client = make()
    first = run(repository.create_progression(ProgressionRecord(owner_id="uid-1", name="Uno", chords=["C", "G"], tonality="C")))
    second = run(repository.create_progression(ProgressionRecord(owner_id="uid-1", name="Dos", chords=["Am", "F"], is_public=True)))
    run(repository.create_progression(ProgressionRecord(owner_id="uid-2", name="Ajena", chords=["D"])))

    assert first.id and first.id in client.store["cw_progressions"]
    assert client.store["cw_progressions"][second.id]["ownerId"] == "uid-1"
    assert client.store["cw_progressions"][second.id]["isPublic"] is True

    # Touching the first one makes it the most recent.
    client.store["cw_progressions"][second.id]["updatedAt"] = utcnow() - timedelta(minutes=5)
    updated = run(repository.update_progression(ProgressionRecord(**{**first.__dict__, "name": "Uno bis"})))
    assert updated.updated_at > first.updated_at

    names = [item.name for item in run(repository.list_progressions("uid-1"))]
    assert names == ["Uno bis", "Dos"]
    fetched = run(repository.get_progression(second.id))
    assert fetched is not None and fetched.chords == ["Am", "F"]

    run(repository.delete_progression(second.id))
    assert run(repository.get_progression(second.id)) is None


def test_deleting_a_user_removes_their_progressions_in_batches(monkeypatch):
    monkeypatch.setattr(firestore_module, "BATCH_LIMIT", 2)
    repository, client = make()
    run(repository.save_user(UserRecord(id="uid-1")))
    for index in range(3):
        run(repository.create_progression(ProgressionRecord(owner_id="uid-1", name=f"P{index}", chords=["C"])))
    keep = run(repository.create_progression(ProgressionRecord(owner_id="uid-2", name="Otra", chords=["C"])))

    run(repository.delete_user("uid-1"))

    assert client.store["cw_users"] == {}
    assert list(client.store["cw_progressions"]) == [keep.id]
    assert client.batch_sizes == [2, 2]  # 3 progressions + the user document.
