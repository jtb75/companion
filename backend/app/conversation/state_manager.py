import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.db.redis import SESSION_TTL, get_redis, session_key

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ConversationState:
    session_id: str
    user_id: str
    current_topic: str | None = None
    messages: list[Message] = field(default_factory=list)
    active_task: dict | None = None
    task_stack: list[dict] = field(default_factory=list)
    started_at: str = ""
    last_activity: str = ""

    def __post_init__(self):
        now = datetime.utcnow().isoformat()
        if not self.started_at:
            self.started_at = now
        if not self.last_activity:
            self.last_activity = now

    def add_message(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))
        self.last_activity = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "current_topic": self.current_topic,
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in self.messages
            ],
            "active_task": self.active_task,
            "task_stack": self.task_stack,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        messages = [
            Message(**m) for m in data.get("messages", [])
        ]
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            current_topic=data.get("current_topic"),
            messages=messages,
            active_task=data.get("active_task"),
            task_stack=data.get("task_stack", []),
            started_at=data.get("started_at", ""),
            last_activity=data.get("last_activity", ""),
        )


class ConversationStateManager:
    """Manages conversation sessions in Redis."""

    async def create_session(self, user_id: str) -> ConversationState:
        sid = str(uuid.uuid4())
        state = ConversationState(session_id=sid, user_id=user_id)
        await self._save(state)
        return state

    async def get_session(self, user_id: str, session_id: str) -> ConversationState | None:
        r = get_redis()
        try:
            key = session_key(user_id, session_id)
            raw = await r.get(key)
            if raw is None:
                return None
            return ConversationState.from_dict(json.loads(raw))
        finally:
            await r.aclose()

    async def get_active_session(self, user_id: str) -> ConversationState | None:
        """Get the most recent active session for a user."""
        r = get_redis()
        try:
            # Scan for session keys for this user
            pattern = session_key(user_id, "*")
            keys = []
            async for key in r.scan_iter(match=pattern, count=10):
                keys.append(key)
            if not keys:
                return None
            # Get the most recent one (by last_activity)
            best = None
            for key in keys:
                raw = await r.get(key)
                if raw:
                    state = ConversationState.from_dict(json.loads(raw))
                    if best is None or state.last_activity > best.last_activity:
                        best = state
            return best
        finally:
            await r.aclose()

    async def update_session(self, state: ConversationState):
        await self._save(state)

    async def end_session(self, user_id: str, session_id: str) -> bool:
        r = get_redis()
        try:
            key = session_key(user_id, session_id)
            result = await r.delete(key)
            return result > 0
        finally:
            await r.aclose()

    async def _save(self, state: ConversationState):
        r = get_redis()
        try:
            key = session_key(state.user_id, state.session_id)
            await r.set(key, json.dumps(state.to_dict()), ex=SESSION_TTL)
        finally:
            await r.aclose()


state_manager = ConversationStateManager()
