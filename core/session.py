"""
Session and barcode data management.
"""
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class BarcodeEntry:
    value: str
    timestamp: datetime
    session_id: int
    sequence: int  # within the session


@dataclass
class Session:
    id: int
    started_at: datetime
    name: str = ""
    price_type: Optional[str] = None  # selected price list for this session
    entries: List[BarcodeEntry] = field(default_factory=list)
    _counts: Counter = field(default_factory=Counter, repr=False)

    def add_barcode(self, value: str) -> BarcodeEntry:
        entry = BarcodeEntry(
            value=value,
            timestamp=datetime.now(),
            session_id=self.id,
            sequence=len(self.entries) + 1,
        )
        self.entries.append(entry)
        self._counts[value] += 1
        return entry

    def count_for(self, value: str) -> int:
        """How many times *value* has been scanned in this session."""
        return self._counts[value]

    def clear_entries(self) -> None:
        """Drop all scans (used by Reset) while keeping the session active."""
        self.entries.clear()
        self._counts.clear()

    def increment(self, value: str) -> None:
        """Manually bump a product's quantity by one (like an extra scan)."""
        self.add_barcode(value)

    def decrement(self, value: str) -> None:
        """Manually lower a product's quantity by one (never below one)."""
        if self._counts.get(value, 0) <= 1:
            return
        for i in range(len(self.entries) - 1, -1, -1):
            if self.entries[i].value == value:
                del self.entries[i]
                break
        self._counts[value] -= 1

    def remove_product(self, value: str) -> None:
        """Remove a product from the session entirely."""
        self.entries = [e for e in self.entries if e.value != value]
        self._counts.pop(value, None)

    def aggregated(self):
        """Unique barcodes in first-scan order as (value, count, last_timestamp)."""
        order: List[str] = []
        last_ts = {}
        for e in self.entries:
            if e.value not in last_ts:
                order.append(e.value)
            last_ts[e.value] = e.timestamp
        return [(v, self._counts[v], last_ts[v]) for v in order]

    def last_value(self) -> Optional[str]:
        """The barcode of the most recent scan, or None if the session is empty."""
        return self.entries[-1].value if self.entries else None

    @property
    def count(self) -> int:
        return len(self.entries)

    # -- serialization (for saving/restoring on exit) ------------------- #

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "started_at": self.started_at.isoformat(),
            "price_type": self.price_type,
            "entries": [
                {
                    "value": e.value,
                    "timestamp": e.timestamp.isoformat(),
                    "sequence": e.sequence,
                }
                for e in self.entries
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        session = cls(
            id=data["id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            name=data.get("name", f"Session {data['id']}"),
            price_type=data.get("price_type"),
        )
        for ed in data.get("entries", []):
            entry = BarcodeEntry(
                value=ed["value"],
                timestamp=datetime.fromisoformat(ed["timestamp"]),
                session_id=session.id,
                sequence=ed.get("sequence", len(session.entries) + 1),
            )
            session.entries.append(entry)
            session._counts[entry.value] += 1
        return session


class SessionManager:
    def __init__(self):
        self._sessions: List[Session] = []
        self._current: Optional[Session] = None
        self._session_counter = 0

    @property
    def current(self) -> Optional[Session]:
        return self._current

    @property
    def is_active(self) -> bool:
        return self._current is not None

    @property
    def sessions(self) -> List[Session]:
        """All open sessions, in creation order."""
        return list(self._sessions)

    def _next_default_name(self) -> str:
        """Lowest 'Session N' not currently used by an open session."""
        existing = {s.name for s in self._sessions}
        n = 1
        while f"Session {n}" in existing:
            n += 1
        return f"Session {n}"

    def start_session(self) -> Session:
        # id stays a monotonic, never-reused identity; the display name reuses
        # the lowest free "Session N" slot among the currently open sessions.
        self._session_counter += 1
        session = Session(
            id=self._session_counter,
            started_at=datetime.now(),
            name=self._next_default_name(),
        )
        self._sessions.append(session)
        self._current = session
        return session

    def select_session(self, session: Session) -> None:
        """Make *session* the active one."""
        if session in self._sessions:
            self._current = session

    def delete_session(self, session: Session) -> Optional[Session]:
        """Remove *session*. If it was active, activate a neighbour. Returns the
        new active session (or None if none remain)."""
        if session not in self._sessions:
            return self._current
        idx = self._sessions.index(session)
        self._sessions.remove(session)
        if self._current is session:
            if self._sessions:
                self._current = self._sessions[min(idx, len(self._sessions) - 1)]
            else:
                self._current = None
        return self._current

    def reset_session(self):
        """Clear current session entries (keeps session active, just clears table)."""
        if self._current is not None:
            self._current.clear_entries()

    def stop_session(self):
        self._current = None

    def add_barcode(self, value: str) -> Optional[BarcodeEntry]:
        if self._current is None:
            return None
        return self._current.add_barcode(value)

    def all_entries(self) -> List[BarcodeEntry]:
        if self._current is None:
            return []
        return list(self._current.entries)

    # -- serialization (for saving/restoring on exit) ------------------- #

    def to_dict(self) -> dict:
        return {
            "session_counter": self._session_counter,
            "active_id": self._current.id if self._current else None,
            "sessions": [s.to_dict() for s in self._sessions],
        }

    def load_state(self, data: dict) -> Optional[Session]:
        """Replace all sessions from *data*. Returns the restored active session."""
        self._sessions = [Session.from_dict(s) for s in data.get("sessions", [])]
        self._session_counter = data.get("session_counter", len(self._sessions))
        self._current = None
        active_id = data.get("active_id")
        if active_id is not None:
            self._current = next(
                (s for s in self._sessions if s.id == active_id), None
            )
        if self._current is None and self._sessions:
            self._current = self._sessions[0]
        return self._current
