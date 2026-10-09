"""Minimal stand-in for google.cloud.firestore.AsyncClient (only what the repository uses)."""

import copy
from uuid import uuid4


class FakeSnapshot:
    def __init__(self, reference: "FakeDocument", data: dict | None):
        self.reference = reference
        self.id = reference.id
        self.exists = data is not None
        self._data = copy.deepcopy(data)

    def to_dict(self) -> dict | None:
        return copy.deepcopy(self._data)


class FakeDocument:
    def __init__(self, store: dict, collection: str, doc_id: str):
        self._store, self._collection, self.id = store, collection, doc_id

    async def get(self) -> FakeSnapshot:
        return FakeSnapshot(self, self._store.setdefault(self._collection, {}).get(self.id))

    async def set(self, data: dict) -> None:
        self._store.setdefault(self._collection, {})[self.id] = copy.deepcopy(data)

    async def delete(self) -> None:
        self._store.setdefault(self._collection, {}).pop(self.id, None)


class FakeQuery:
    def __init__(self, collection: "FakeCollection", filters: list):
        self._collection, self._filters = collection, filters

    def where(self, *, filter) -> "FakeQuery":
        return FakeQuery(self._collection, [*self._filters, filter])

    async def stream(self):
        for doc_id, data in list(self._collection.docs().items()):
            if all(f.op_string == "==" and data.get(f.field_path) == f.value for f in self._filters):
                yield FakeSnapshot(self._collection.document(doc_id), data)

    def count(self) -> "FakeCountQuery":
        return FakeCountQuery(self)


class FakeAggregationResult:
    def __init__(self, value: int):
        self.value = value


class FakeCountQuery:
    """Mirrors AsyncAggregationQuery: get() returns [[AggregationResult]]."""

    def __init__(self, query: FakeQuery):
        self._query = query

    async def get(self) -> list[list[FakeAggregationResult]]:
        total = len([snapshot async for snapshot in self._query.stream()])
        return [[FakeAggregationResult(total)]]


class FakeCollection(FakeQuery):
    def __init__(self, store: dict, name: str):
        self._store, self.name = store, name
        super().__init__(self, [])

    def docs(self) -> dict:
        return self._store.setdefault(self.name, {})

    def document(self, doc_id: str | None = None) -> FakeDocument:
        return FakeDocument(self._store, self.name, doc_id or uuid4().hex[:20])


class FakeBatch:
    def __init__(self, client: "FakeFirestore"):
        self._client, self._deletes = client, []

    def delete(self, reference: FakeDocument) -> None:
        self._deletes.append(reference)

    async def commit(self) -> None:
        self._client.batch_sizes.append(len(self._deletes))
        for reference in self._deletes:
            await reference.delete()


class FakeFirestore:
    def __init__(self):
        self.store: dict[str, dict[str, dict]] = {}
        self.batch_sizes: list[int] = []

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self.store, name)

    def batch(self) -> FakeBatch:
        return FakeBatch(self)
