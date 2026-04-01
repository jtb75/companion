"""App API — Conversation (D.D.) routes."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.auth.dependencies import User, require_complete_profile
from app.conversation.llm import get_llm_client
from app.conversation.prompt_builder import build_system_prompt
from app.conversation.state_manager import state_manager
from app.db import get_db
from app.models.system_config import SystemConfig
from app.schemas.conversation import (
    ConversationMessageRequest,
    ConversationStartRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["Conversation"])

DEFAULT_CONTEXT_WINDOW = 20


async def _get_context_window(db: AsyncSession) -> int:
    """Get context window size from system_config."""
    try:
        result = await db.execute(
            select(SystemConfig).where(
                SystemConfig.category == "dd_persona",
                SystemConfig.key == "context_window",
                SystemConfig.is_active.is_(True),
            )
        )
        config = result.scalar_one_or_none()
        if config and config.value:
            return int(config.value.get(
                "max_messages", DEFAULT_CONTEXT_WINDOW
            ))
    except Exception:
        pass
    return DEFAULT_CONTEXT_WINDOW


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
        system_prompt, greeting_messages, max_tokens=1024
    )

    session.add_message("assistant", greeting)
    await state_manager.update_session(session)

    # Persist chat session to DB for audit
    from datetime import datetime as dt

    from app.models.chat_session import (
        ChatMessage,
        ChatSession,
    )

    db_session = ChatSession(
        user_id=user.id,
        session_id=session.session_id,
        started_at=dt.utcnow(),
        message_count=1,
    )
    db.add(db_session)
    await db.flush()
    db.add(
        ChatMessage(
            chat_session_id=db_session.id,
            role="assistant",
            content=greeting,
        )
    )
    await db.commit()

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

    # Apply sliding window to limit context
    window = await _get_context_window(db)
    recent = session.messages[-window:]

    llm_messages = [
        {"role": m.role, "content": m.content}
        for m in recent
    ]

    # Generate response
    llm = get_llm_client()
    response_text = await llm.generate(
        system_prompt, llm_messages, max_tokens=1024
    )

    # Add assistant response to session
    session.add_message("assistant", response_text)
    await state_manager.update_session(session)

    # Persist messages to DB
    try:
        from sqlalchemy import select as sa_select

        from app.models.chat_session import (
            ChatMessage,
            ChatSession,
        )
        result = await db.execute(
            sa_select(ChatSession).where(
                ChatSession.session_id == session.session_id
            )
        )
        db_session = result.scalar_one_or_none()
        if db_session:
            db.add(ChatMessage(
                chat_session_id=db_session.id,
                role="user",
                content=data.text,
            ))
            db.add(ChatMessage(
                chat_session_id=db_session.id,
                role="assistant",
                content=response_text,
            ))
            db_session.message_count += 2
            await db.commit()
    except Exception:
        logger.exception("Failed to persist chat")
        await db.rollback()

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
    window = await _get_context_window(db)
    recent = session.messages[-window:]
    llm_messages = [
        {"role": m.role, "content": m.content}
        for m in recent
    ]
    llm = get_llm_client()

    async def event_generator():
        full_response = ""
        try:
            async for token in llm.generate_stream(
                system_prompt, llm_messages, max_tokens=1024
            ):
                full_response += token
                event = json.dumps({"token": token})
                yield f"data: {event}\n\n"

            # Save full assistant response after stream ends
            session.add_message("assistant", full_response)
            await state_manager.update_session(session)

            # Persist to DB
            try:
                from sqlalchemy import select as sa_sel

                from app.models.chat_session import (
                    ChatMessage,
                    ChatSession,
                )
                res = await db.execute(
                    sa_sel(ChatSession).where(
                        ChatSession.session_id
                        == session.session_id
                    )
                )
                db_sess = res.scalar_one()
                db.add(ChatMessage(
                    chat_session_id=db_sess.id,
                    role="user",
                    content=data.text,
                ))
                db.add(ChatMessage(
                    chat_session_id=db_sess.id,
                    role="assistant",
                    content=full_response,
                ))
                db_sess.message_count += 2
                await db.commit()
            except Exception:
                logger.exception(
                    "Failed to persist streamed chat"
                )
                await db.rollback()

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
    db: AsyncSession = Depends(get_db),
):
    """End the current D.D. session."""
    session = await state_manager.get_active_session(str(user.id))
    if session is None:
        return {"status": "no_active_session"}

    await state_manager.end_session(str(user.id), session.session_id)

    # Mark ended in DB
    from datetime import datetime as dt

    from sqlalchemy import select as s

    from app.models.chat_session import (
        ChatSession as CSe,
    )

    try:
        result = await db.execute(
            s(CSe).where(
                CSe.session_id == session.session_id
            )
        )
        db_session = result.scalar_one()
        db_session.ended_at = dt.utcnow()
        await db.commit()
    except Exception:
        logger.exception("Failed to mark session ended")
        await db.rollback()

    return {
        "status": "ended",
        "session_id": session.session_id,
        "message_count": len(session.messages),
    }
