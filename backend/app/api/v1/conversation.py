"""App API — Conversation (Arlo) routes."""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/conversation", tags=["Conversation"])


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_conversation(user: User = Depends(get_current_user)):
    """Start an Arlo conversation session."""
    # TODO: initialize conversation session
    return {
        "session_id": str(uuid.uuid4()),
        "status": "active",
        "started_at": "2026-03-27T12:00:00Z",
    }


@router.post("/message")
async def send_message(user: User = Depends(get_current_user)):
    """Send a message to Arlo."""
    # TODO: process user message through Arlo conversation engine
    return {
        "message_id": str(uuid.uuid4()),
        "response": "Hi! I'm Arlo, your companion. How can I help you today?",
        "timestamp": "2026-03-27T12:00:01Z",
    }


@router.get("/state")
async def conversation_state(user: User = Depends(get_current_user)):
    """Get current conversation state."""
    # TODO: retrieve active conversation state
    return {
        "session_id": None,
        "status": "inactive",
        "message_count": 0,
    }


@router.post("/end")
async def end_conversation(user: User = Depends(get_current_user)):
    """End the current Arlo session."""
    # TODO: close conversation session, persist summary
    return {
        "status": "ended",
        "ended_at": "2026-03-27T12:30:00Z",
    }
