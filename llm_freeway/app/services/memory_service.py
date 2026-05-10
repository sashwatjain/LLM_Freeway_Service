from collections import OrderedDict

from app.config import settings
from app.schemas import Message


class MemoryService:
    def __init__(self):
        self._sessions: dict[str, "SessionContext"] = {}
        self._char_limit = settings.memory_char_limit

    def get_or_create(self, session_id: str) -> "SessionContext":
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionContext(session_id, self._char_limit)
        return self._sessions[session_id]

    def clear(self, session_id: str):
        self._sessions.pop(session_id, None)


class SessionContext:
    def __init__(self, session_id: str, char_limit: int):
        self.session_id = session_id
        self.messages: list[Message] = []
        self._char_limit = char_limit

    def add_messages(self, new_messages: list[Message]):
        self.messages.extend(new_messages)
        total = sum(len(m.content) for m in self.messages)
        while total > self._char_limit and len(self.messages) > 1:
            dropped = self.messages.pop(0)
            total -= len(dropped.content)

    def get_context(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self.messages]


memory_service = MemoryService()
