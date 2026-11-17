import threading
import time


class SessionStore:
    """Thread-safe in-memory Claude Agent SDK session ID store.

    Stores session IDs keyed by (channel_id, thread_ts, user_id), so each
    requester resumes only their own conversation in a shared thread.
    Includes TTL-based cleanup and a maximum conversation limit.
    """

    def __init__(self, ttl_seconds: int = 86400, max_conversations: int = 1000):
        self._store: dict[tuple[str, str, str], dict] = {}
        self._lock = threading.Lock()
        self._ttl_seconds = ttl_seconds
        self._max_conversations = max_conversations

    def get_session(self, channel_id: str, thread_ts: str, user_id: str) -> str | None:
        """Retrieve the session ID for a requester in a thread.

        Returns None if no session exists or if the session has expired.
        """
        key = (channel_id, thread_ts, user_id)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.time() - entry["timestamp"] > self._ttl_seconds:
                del self._store[key]
                return None
            return entry["session_id"]

    def set_session(
        self, channel_id: str, thread_ts: str, user_id: str, session_id: str
    ) -> None:
        """Store the session ID for a requester in a thread."""
        key = (channel_id, thread_ts, user_id)
        with self._lock:
            self._store[key] = {
                "session_id": session_id,
                "timestamp": time.time(),
            }
            self._cleanup()

    def has_thread(self, channel_id: str, thread_ts: str) -> bool:
        """Check if any unexpired entry exists for a thread."""
        now = time.time()
        with self._lock:
            for (c_id, t_ts, _), entry in self._store.items():
                if (
                    c_id == channel_id
                    and t_ts == thread_ts
                    and now - entry["timestamp"] <= self._ttl_seconds
                ):
                    return True
            return False

    def _cleanup(self) -> None:
        """Remove expired entries and enforce max conversation limit."""
        now = time.time()

        expired = [
            k
            for k, v in self._store.items()
            if now - v["timestamp"] > self._ttl_seconds
        ]
        for k in expired:
            del self._store[k]

        if len(self._store) > self._max_conversations:
            sorted_keys = sorted(
                self._store.keys(), key=lambda k: self._store[k]["timestamp"]
            )
            for k in sorted_keys[: len(self._store) - self._max_conversations]:
                del self._store[k]
