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

    def start_session(self) -> Session:
        self._session_counter += 1
        session = Session(
            id=self._session_counter,
            started_at=datetime.now(),
            name=f"Session {self._session_counter}",
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
