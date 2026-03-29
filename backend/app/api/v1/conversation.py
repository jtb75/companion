"""App API — Conversation (Arlo) routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, require_complete_profile
from app.conversation.llm import get_llm_client
from app.conversation.prompt_builder import build_system_prompt
from app.conversation.state_manager import state_manager
from app.db import get_db
from app.schemas.conversation import (
    ConversationMessageRequest,
    ConversationStartRequest,
)

router = APIRouter(prefix="/conversation", tags=["Conversation"])


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_conversation(
    data: ConversationStartRequest | None = None,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Start an Arlo conversation session."""
    session = await state_manager.create_session(str(user.id))

    # Generate Arlo's greeting
    trigger = "user_initiated"
    if data and data.initial_context:
        trigger = data.initial_context

    system_prompt = await build_system_prompt(db, user, trigger)
    llm = get_llm_client()

    name = user.nickname or user.preferred_name
    greeting_messages = [
        {"role": "user", "content": f"[Session started by {name}]"}
    ]
    greeting = await llm.generate(
        system_prompt, greeting_messages, max_tokens=150
    )

    session.add_message("assistant", greeting)
    await state_manager.update_session(session)

    return {
        "session_id": session.session_id,
        "greeting": greeting,
        "status": "active",
        "started_at": session.started_at,
    }


@router.post("/message")
async def send_message(
    data: ConversationMessageRequest,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to Arlo and get a response."""
    # Find active session
    session = await state_manager.get_active_session(str(user.id))
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="No active conversation. Start one first.",
        )

    # Add user message
    session.add_message("user", data.text)

    # Build prompt with full context
    system_prompt = await build_system_prompt(db, user)

    # Convert session messages to LLM format
    llm_messages = [
        {"role": m.role, "content": m.content}
        for m in session.messages
    ]

    # Generate response
    llm = get_llm_client()
    response_text = await llm.generate(
        system_prompt, llm_messages, max_tokens=300
    )

    # Add assistant response to session
    session.add_message("assistant", response_text)
    await state_manager.update_session(session)

    return {
        "session_id": session.session_id,
        "response": response_text,
        "message_count": len(session.messages),
    }


@router.get("/state")
async def conversation_state(
    user: User = Depends(require_complete_profile),
):
    """Get current conversation state."""
    session = await state_manager.get_active_session(str(user.id))
    if session is None:
        return {
            "session_id": None,
            "status": "inactive",
            "message_count": 0,
        }
    return {
        "session_id": session.session_id,
        "status": "active",
        "message_count": len(session.messages),
        "current_topic": session.current_topic,
        "started_at": session.started_at,
        "last_activity": session.last_activity,
    }


@router.post("/end")
async def end_conversation(
    user: User = Depends(require_complete_profile),
):
    """End the current Arlo session."""
    session = await state_manager.get_active_session(str(user.id))
    if session is None:
        return {"status": "no_active_session"}

    await state_manager.end_session(str(user.id), session.session_id)
    return {
        "status": "ended",
        "session_id": session.session_id,
        "message_count": len(session.messages),
    }
