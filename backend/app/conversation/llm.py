import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    async def generate(
        self, system_prompt: str, messages: list[dict], max_tokens: int = 500
    ) -> str:
        ...

    async def generate_stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        """Yield text chunks. Default: single chunk fallback."""
        text = await self.generate(
            system_prompt, messages, max_tokens
        )
        yield text


class GeminiClient(LLMClient):
    """Gemini via Vertex AI. Uses service account auth (no API key needed)."""

    def __init__(self):
        self._initialized = False

    def _ensure_init(self):
        if not self._initialized:
            try:
                import vertexai
                vertexai.init(
                    project=settings.gcp_project_id,
                    location=settings.gemini_location,
                )
                self._initialized = True
            except Exception:
                logger.exception("Vertex AI init failed")

    def _get_model(self, system_prompt: str = ""):
        self._ensure_init()
        if not self._initialized:
            return None
        try:
            from vertexai.generative_models import (
                GenerativeModel,
            )
            return GenerativeModel(
                settings.gemini_model,
                system_instruction=system_prompt,
            )
        except Exception:
            logger.exception("Gemini model init failed")
            return None

    async def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 500,
    ) -> str:
        model = self._get_model(system_prompt)
        if model is None:
            return self._fallback_response(messages)

        try:
            from vertexai.generative_models import (
                Content,
                GenerationConfig,
                Part,
            )

            contents = []
            for msg in messages:
                role = (
                    "user"
                    if msg["role"] == "user"
                    else "model"
                )
                contents.append(
                    Content(
                        role=role,
                        parts=[Part.from_text(msg["content"])],
                    )
                )

            response = await model.generate_content_async(
                contents,
                generation_config=GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                ),
            )
            return response.text
        except Exception:
            logger.exception("Gemini API call failed")
            return self._fallback_response(messages)

    async def generate_stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        model = self._get_model(system_prompt)
        if model is None:
            yield self._fallback_response(messages)
            return

        try:
            from vertexai.generative_models import (
                Content,
                GenerationConfig,
                Part,
            )

            contents = []
            for msg in messages:
                role = (
                    "user" if msg["role"] == "user" else "model"
                )
                contents.append(
                    Content(
                        role=role,
                        parts=[Part.from_text(msg["content"])],
                    )
                )

            response = await model.generate_content_async(
                contents,
                stream=True,
                generation_config=GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                ),
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception:
            logger.exception("Gemini streaming failed")
            yield self._fallback_response(messages)

    def _fallback_response(self, messages: list[dict]) -> str:
        last = messages[-1]["content"] if messages else ""
        return (
            f"I heard you say: \"{last[:100]}\". "
            "I'm having a little trouble connecting right now. "
            "Can you try again in a moment?"
        )


class ClaudeClient(LLMClient):
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(
                    api_key=settings.anthropic_api_key
                )
            except Exception:
                logger.warning("Anthropic client unavailable")
        return self._client

    async def generate(
        self, system_prompt: str, messages: list[dict], max_tokens: int = 500
    ) -> str:
        client = self._get_client()
        if client is None or not settings.anthropic_api_key:
            return self._fallback_response(messages)

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            )
            return response.content[0].text
        except Exception:
            logger.exception("Claude API call failed")
            return self._fallback_response(messages)

    def _fallback_response(self, messages: list[dict]) -> str:
        last = messages[-1]["content"] if messages else ""
        return (
            f"I heard you say: \"{last[:100]}\". "
            "I'm having a little trouble connecting right now. "
            "Can you try again in a moment?"
        )


class OpenAIClient(LLMClient):
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(
                    api_key=settings.openai_api_key
                )
            except Exception:
                logger.warning("OpenAI client unavailable")
        return self._client

    async def generate(
        self, system_prompt: str, messages: list[dict], max_tokens: int = 500
    ) -> str:
        client = self._get_client()
        if client is None or not settings.openai_api_key:
            return self._fallback_response(messages)

        try:
            full_messages = [
                {"role": "system", "content": system_prompt}
            ] + messages
            response = await client.chat.completions.create(
                model="gpt-4o",
                max_tokens=max_tokens,
                messages=full_messages,
            )
            return response.choices[0].message.content
        except Exception:
            logger.exception("OpenAI API call failed")
            return self._fallback_response(messages)

    def _fallback_response(self, messages: list[dict]) -> str:
        last = messages[-1]["content"] if messages else ""
        return (
            f"I heard you say: \"{last[:100]}\". "
            "I'm having a little trouble right now. "
            "Can you try again?"
        )


def get_llm_client() -> LLMClient:
    """Get the configured LLM client."""
    if settings.llm_provider == "openai":
        return OpenAIClient()
    if settings.llm_provider == "anthropic":
        return ClaudeClient()
    return GeminiClient()
