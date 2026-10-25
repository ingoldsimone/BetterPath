"""In-memory stand-in for the MongoDB collections, used when MONGO_URI is not set.

It supports only the calls the app makes on a collection, `find(filter)`
(iterated with `async for`) and `await insert_one(doc)`, so the rest of
the code works unchanged. The graph is loaded from the JSON exports in
data/; reported obstacles are kept in memory and reset when the server
restarts.
"""
import copy
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class _InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _Cursor:
    def __init__(self, docs):
        self._docs = iter(docs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._docs)
        except StopIteration:
            raise StopAsyncIteration


class InMemoryCollection:
    def __init__(self, docs=None):
        self._docs = list(docs or [])

    def find(self, filter=None):
        filter = filter or {}
        matches = [
            copy.deepcopy(doc)
            for doc in self._docs
            if all(doc.get(key) == value for key, value in filter.items())
        ]
        return _Cursor(matches)

    async def insert_one(self, doc):
        self._docs.append(copy.deepcopy(doc))
        return _InsertResult(doc.get("_id"))


def _load(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def load_demo_collections():
    """Return (obstacles, nodes, edges) collections seeded from data/."""
    return (
        InMemoryCollection(),
        InMemoryCollection(_load("graph_nodes.json")),
        InMemoryCollection(_load("graph_edges.json")),
    )
