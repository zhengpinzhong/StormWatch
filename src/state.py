"""Persistent state management for notification deduplication."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"


@dataclass
class AppState:
    """Application state persisted between runs."""

    notified_keys: set[str] = field(default_factory=set)
    last_daily_sent: str | None = None

    def has_notified(self, key: str) -> bool:
        return key in self.notified_keys

    def mark_notified(self, key: str) -> None:
        self.notified_keys.add(key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "notified_keys": sorted(self.notified_keys),
            "last_daily_sent": self.last_daily_sent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppState":
        keys = data.get("notified_keys", [])
        if not isinstance(keys, list):
            keys = []
        return cls(
            notified_keys=set(str(key) for key in keys),
            last_daily_sent=data.get("last_daily_sent"),
        )


def load_state(path: Path | None = None) -> AppState:
    """Load state from disk, returning empty state if file is missing."""
    state_path = path or DEFAULT_STATE_PATH
    if not state_path.exists():
        return AppState()
    with state_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        return AppState()
    return AppState.from_dict(data)


def save_state(state: AppState, path: Path | None = None) -> None:
    """Persist state to disk."""
    state_path = path or DEFAULT_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as handle:
        json.dump(state.to_dict(), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
