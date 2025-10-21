"""Incremental caching helpers for translation workflows."""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class CachedLine:
    """Represents a cached line of source text."""

    text: str
    digest: str
    timestamp: float


class LineCache:
    """Cache utility that tracks the most recent lines processed by the model.

    The cache keeps up to ``max_lines`` entries. When new text is supplied via
    :meth:`update`, the cache computes hashes for each line and returns the
    subset of lines whose hashes differ from what is currently stored. This is
    sufficient for translation workflows where input is typically processed
    line-by-line or sentence-by-sentence.
    """

    def __init__(self, max_lines: int = 128) -> None:
        self.max_lines = max_lines
        self._entries: "OrderedDict[str, CachedLine]" = OrderedDict()

    @staticmethod
    def _digest(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()

    def update(self, lines: Sequence[str]) -> List[str]:
        """Update the cache with *lines* and return only the changed entries.

        Parameters
        ----------
        lines:
            Sequence of input lines (typically the text split on newlines).

        Returns
        -------
        list[str]
            A list containing only the lines whose content differs from the
            cached version. This allows callers to skip re-processing identical
            text across subsequent invocations.
        """

        changed: List[str] = []
        timestamp = time.time()

        for line in lines:
            digest = self._digest(line)
            cached = self._entries.get(line)
            if cached and cached.digest == digest:
                cached.timestamp = timestamp
                continue

            changed.append(line)
            self._entries[line] = CachedLine(line, digest, timestamp)
            self._entries.move_to_end(line)

            if len(self._entries) > self.max_lines:
                self._entries.popitem(last=False)

        return changed

    def prune(self, ttl: float) -> None:
        """Remove entries older than *ttl* seconds."""

        now = time.time()
        keys_to_delete = [
            key
            for key, cached in self._entries.items()
            if now - cached.timestamp > ttl
        ]
        for key in keys_to_delete:
            self._entries.pop(key, None)

    def __contains__(self, line: str) -> bool:  # pragma: no cover - trivial
        return line in self._entries

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._entries)


__all__ = ["LineCache", "CachedLine"]
