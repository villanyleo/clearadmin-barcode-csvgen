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

    def start_session(self) -> Session:
        self._session_counter += 1
        session = Session(id=self._session_counter, started_at=datetime.now())
        self._sessions.append(session)
        self._current = session
        return session

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
