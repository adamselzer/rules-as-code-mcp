"""In-memory store of determinations, so they can be explained later by id.

A determination id is a reproducible hash of its inputs, so this store is a
convenience cache, not the source of truth: a determination can always be
recomputed. Only caseworker-scope tools write to or read from it, which keeps
the no-PII-in-screening boundary intact.

In production this would be a database with retention and audit logging; here it
is a process-local dict, sufficient for the demonstration and the eval.
"""

from __future__ import annotations

from rules.models import Determination


class DeterminationStore:
    def __init__(self) -> None:
        self._by_id: dict[str, Determination] = {}

    def put(self, determination: Determination) -> None:
        self._by_id[determination.determination_id] = determination

    def get(self, determination_id: str) -> Determination | None:
        return self._by_id.get(determination_id)

    def __len__(self) -> int:
        return len(self._by_id)


# Process-local singleton used by the server tools.
STORE = DeterminationStore()
