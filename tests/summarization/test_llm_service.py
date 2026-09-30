"""Tests for app.services.llm_service.

These tests never construct a real OpenAI client or make a network call.
``OpenAILLMService`` lazily imports/constructs the client only inside
``complete()``, so simply instantiating it (with no key) is safe, and the
"no API key configured" path is what's exercised here.
"""

from __future__ import annotations

import pytest

from app.services.llm_service import (
    LLMServiceError,
    OpenAILLMService,
    get_llm_service,
)


@pytest.mark.asyncio
async def test_openai_service_raises_clear_error_without_api_key(monkeypatch):
    # OpenAILLMService(api_key=None, ...) falls back to settings.openai_api_key
    # inside __init__. If the machine running the suite happens to have a
    # real OPENAI_API_KEY in its environment, that fallback would silently
    # pick it up and this test would make a real (billed) network call
    # instead of exercising the "no key configured" path. Pin settings to a
    # fake with no key so the test is deterministic regardless of the
    # environment it runs in.
    monkeypatch.setattr("app.services.llm_service.settings", lambda: _FakeSettings("openai"))

    service = OpenAILLMService(api_key=None, model="gpt-4o-mini")

    with pytest.raises(LLMServiceError, match="No OpenAI API key configured"):
        await service.complete(system="sys", user="usr")


def test_get_llm_service_returns_openai_service_by_default(monkeypatch):
    monkeypatch.setattr("app.services.llm_service.settings", lambda: _FakeSettings("openai"))
    service = get_llm_service()
    assert isinstance(service, OpenAILLMService)


def test_get_llm_service_raises_for_unsupported_provider(monkeypatch):
    monkeypatch.setattr("app.services.llm_service.settings", lambda: _FakeSettings("not-a-real-provider"))
    with pytest.raises(LLMServiceError, match="Unsupported llm_provider"):
        get_llm_service()


class _FakeSettings:
    def __init__(self, llm_provider: str):
        self.llm_provider = llm_provider
        self.openai_api_key = None
        self.llm_model = "gpt-4o-mini"
