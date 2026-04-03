"""Service for generating LLM-powered personalized briefings."""

import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.llm import get_llm_client
from app.conversation.persona import DD_PERSONA

logger = logging.getLogger(__name__)

MORNING_BRIEFING_PROMPT = """You are a warm, supportive independence assistant.
Your task is to turn a structured list of today's items into a very short, spoken morning briefing.

GUIDELINES:
- Keep it under 3 sentences.
- Target a 4th-6th grade reading level (Easy Read).
- Focus only on the most urgent thing first.
- End with a reassuring "I'm here if you need help."

INPUT DATA:
{checkin_json}

EXAMPLE OUTPUT:
"Good morning! You have a doctor's appointment at 2:00 PM today. We should leave by 1:15 PM. I'm here if you need help."
"""

async def generate_morning_briefing(
    db: AsyncSession,
    user_id: UUID,
    checkin_data: dict,
) -> str:
    """Use the LLM to create a personalized morning briefing string."""
    try:
        llm = get_llm_client()
        
        # Prepare the input for the LLM
        # We strip some fields to keep the prompt clean
        clean_data = {
            "greeting": checkin_data.get("greeting"),
            "urgent_items": checkin_data.get("urgent_items", []),
            "today_items": checkin_data.get("today_items", []),
            "total_items": checkin_data.get("total_items", 0),
        }
        
        checkin_json = json.dumps(clean_data, indent=2)
        
        prompt = MORNING_BRIEFING_PROMPT.format(checkin_json=checkin_json)
        
        briefing = await llm.generate(
            system_prompt=DD_PERSONA,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        
        return briefing.strip().strip('"')
    except Exception:
        logger.exception("Failed to generate morning briefing via LLM")
        # Fallback to the hardcoded text from assemble_morning_checkin
        urgent = checkin_data.get("urgent", "")
        today = checkin_data.get("today", "")
        return f"{urgent} {today}".strip() or "You have a few things to look at today."
