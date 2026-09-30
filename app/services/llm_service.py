"""LLM service abstraction with OpenAI and Groq support."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Raised when an LLM call fails."""


class LLMService(ABC):
    """Interface implemented by LLM providers."""

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 700,
    ) -> str:
        """Return a text completion."""
        raise NotImplementedError


class OpenAILLMService(LLMService):
    """LLM service backed by OpenAI or an OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: str = "openai",
    ) -> None:

        self._provider = provider.lower()
        self._model = model or settings.LLM_MODEL
        self._client = None

        if self._provider == "groq":
            self._api_key = api_key or settings.GROQ_API_KEY
            self._base_url = (
                base_url or "https://api.groq.com/openai/v1"
            )
        else:
            self._api_key = api_key or settings.OPENAI_API_KEY
            self._base_url = base_url

    def _get_client(self):
        if self._client is not None:
            return self._client

        if not self._api_key:
            if self._provider == "groq":
                raise LLMServiceError(
                    "No Groq API key configured. "
                    "Set GROQ_API_KEY in .env."
                )

            raise LLMServiceError(
                "No OpenAI API key configured. "
                "Set OPENAI_API_KEY in .env."
            )

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise LLMServiceError(
                "The 'openai' package is required for the LLM service. "
                "Install it with `pip install openai`."
            ) from exc

        client_kwargs = {
            "api_key": self._api_key,
        }

        if self._base_url:
            client_kwargs["base_url"] = self._base_url

        self._client = AsyncOpenAI(**client_kwargs)

        return self._client

    async def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 700,
    ) -> str:
        client = self._get_client()

        try:
            response = await client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "system",
                        "content": system,
                    },
                    {
                        "role": "user",
                        "content": user,
                    },
                ],
            )

        except Exception as exc:
            provider_name = self._provider.capitalize()

            # Keep rate-limit information visible to the caller.
            status_code = getattr(exc, "status_code", None)

            if status_code == 429:
                raise LLMServiceError(
                    f"{provider_name} rate limit exceeded. "
                    "Please wait before sending another request."
                ) from exc

            raise LLMServiceError(
                f"{provider_name} completion request failed: {exc}"
            ) from exc

        if (
            not response.choices
            or not response.choices[0].message
            or not response.choices[0].message.content
        ):
            raise LLMServiceError(
                f"{self._provider.capitalize()} response contained no content"
            )

        return response.choices[0].message.content


class GroqLLMService(OpenAILLMService):
    """LLM service backed by Groq's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            base_url="https://api.groq.com/openai/v1",
            provider="groq",
        )


def get_llm_service() -> LLMService:
    """Return the configured LLM service."""

    provider = (settings.LLM_PROVIDER or "").strip().lower()

    if provider == "groq":
        return GroqLLMService()

    if provider == "openai":
        return OpenAILLMService(
            provider="openai",
        )

    raise LLMServiceError(
        f"Unsupported llm_provider '{settings.LLM_PROVIDER}'. "
        "Supported providers are: 'openai', 'groq'."
    )