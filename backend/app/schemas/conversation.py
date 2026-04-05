from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationStartRequest(BaseModel):
    initial_context: str | None = Field(
        default=None,
        description="Optional context for the conversation",
    )


class ConversationMessageRequest(BaseModel):
    text: str = Field(description="User message text")
    audio_data: str | None = Field(
        default=None,
        description="Base64-encoded audio data (optional)",
    )


class ConversationResponse(BaseModel):
    session_id: str
    response_text: str
    audio_data: str | None = None


class ConversationStateResponse(BaseModel):
    session_id: str
    current_topic: str | None = None
    active_task: str | None = None
