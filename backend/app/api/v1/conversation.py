"""App API — Conversation (D.D.) routes."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.auth.dependencies import User, require_complete_profile
from app.conversation.llm import get_llm_client
from app.conversation.prompt_builder import build_system_prompt
from app.conversation.state_manager import state_manager
from app.db import get_db
from app.schemas.conversation import (
    ConversationMessageRequest,
    ConversationStartRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["Conversation"])


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_conversation(
    data: ConversationStartRequest | None = None,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Start a D.D. conversation session."""
    session = await state_manager.create_session(str(user.id))

    # Generate D.D.'s greeting
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
        system_prompt, greeting_messages, max_tokens=300
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
    """Send a message to D.D. and get a response."""
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


@router.post("/message/stream")
async def send_message_stream(
    data: ConversationMessageRequest,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Stream a D.D. response via SSE."""
    session = await state_manager.get_active_session(
        str(user.id)
    )
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="No active conversation. Start one first.",
        )

    # Add user message before streaming
    session.add_message("user", data.text)
    await state_manager.update_session(session)

    system_prompt = await build_system_prompt(db, user)
    llm_messages = [
        {"role": m.role, "content": m.content}
        for m in session.messages
    ]
    llm = get_llm_client()

    async def event_generator():
        full_response = ""
        try:
            async for token in llm.generate_stream(
                system_prompt, llm_messages, max_tokens=300
            ):
                full_response += token
                event = json.dumps({"token": token})
                yield f"data: {event}\n\n"

            # Save full assistant response after stream ends
            session.add_message("assistant", full_response)
            await state_manager.update_session(session)

            done_event = json.dumps(
                {"done": True, "full_response": full_response}
            )
            yield f"data: {done_event}\n\n"
        except Exception:
            logger.exception("SSE stream error")
            if not full_response:
                full_response = (
                    "Sorry, something went wrong. "
                    "Please try again."
                )
                session.add_message(
                    "assistant", full_response
                )
                await state_manager.update_session(session)
            err = json.dumps(
                {"error": True, "full_response": full_response}
            )
            yield f"data: {err}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


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
    """End the current D.D. session."""
    session = await state_manager.get_active_session(str(user.id))
    if session is None:
        return {"status": "no_active_session"}

    await state_manager.end_session(str(user.id), session.session_id)
    return {
        "status": "ended",
        "session_id": session.session_id,
        "message_count": len(session.messages),
    }
