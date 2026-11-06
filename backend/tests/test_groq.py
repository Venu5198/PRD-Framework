import pytest
import json
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.ai.groq_adapter import GroqAdapter
from app.ai.ollama_adapter import OllamaAdapter
from app.ai.offline_adapter import OfflineMockAdapter
from app.ai.factory import get_ai_gateway, reset_cached_gateway
from app.ai.exceptions import (
    GroqAuthError,
    GroqRateLimitError,
    GroqTimeoutError,
    GroqGenerationError,
    InvalidModelResponseError
)
from app.core.config import settings

@pytest.mark.asyncio
async def test_groq_missing_api_key_auth_error():
    """Verify missing API key raises GroqAuthError without making HTTP calls."""
    adapter = GroqAdapter(api_key=None, base_url="https://api.groq.com/openai/v1")
    adapter.api_key = None  # Ensure explicitly None

    # is_available returns False when API key is missing
    assert await adapter.is_available() is False
    assert await adapter.list_models() == []

    # generate raises GroqAuthError
    with pytest.raises(GroqAuthError) as exc_info:
        await adapter.generate("Test prompt")
    assert "GROQ_API_KEY" in str(exc_info.value)

@pytest.mark.asyncio
async def test_groq_successful_text_generation():
    """Verify successful text generation via mocked Groq completion API."""
    adapter = GroqAdapter(api_key="mock_key_12345", base_url="https://api.groq.com/openai/v1", model="openai/gpt-oss-120b")
    mock_response_data = {
        "id": "chatcmpl-mock",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a high quality response from Groq."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 8,
            "total_tokens": 23
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await adapter.generate(
            prompt="Generate a system description",
            system_instruction="You are a Principal Architect",
            temperature=0.3
        )

        assert result == "This is a high quality response from Groq."
        assert mock_post.called
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["model"] == "openai/gpt-oss-120b"
        assert len(call_kwargs["json"]["messages"]) == 2
        assert call_kwargs["json"]["messages"][0]["role"] == "system"
        assert call_kwargs["json"]["messages"][1]["role"] == "user"
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer mock_key_12345"

@pytest.mark.asyncio
async def test_groq_structured_json_generation():
    """Verify json_mode enforces response_format and validates JSON parsing."""
    adapter = GroqAdapter(api_key="mock_key_12345", base_url="https://api.groq.com/openai/v1")
    valid_json_payload = {"status": "ok", "items": ["req1", "req2"]}
    mock_response_data = {
        "id": "chatcmpl-json",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(valid_json_payload)
                }
            }
        ],
        "usage": {"total_tokens": 30}
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await adapter.generate(
            prompt="Return JSON",
            json_mode=True
        )

        parsed = json.loads(result)
        assert parsed["status"] == "ok"
        assert len(parsed["items"]) == 2

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["response_format"] == {"type": "json_object"}

@pytest.mark.asyncio
async def test_groq_invalid_json_mode_rejection():
    """Verify invalid JSON text when json_mode=True raises InvalidModelResponseError."""
    adapter = GroqAdapter(api_key="mock_key_12345", base_url="https://api.groq.com/openai/v1")
    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": "This is plain text, not JSON"
                }
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(InvalidModelResponseError) as exc_info:
            await adapter.generate("Return JSON", json_mode=True)
        assert "json_mode contract" in str(exc_info.value)

@pytest.mark.asyncio
async def test_groq_authentication_failure():
    """Verify HTTP 401/403 triggers GroqAuthError without exposing secrets."""
    adapter = GroqAdapter(api_key="invalid_bad_key", base_url="https://api.groq.com/openai/v1")
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(GroqAuthError) as exc_info:
            await adapter.generate("Test prompt")
        assert "authentication rejected" in str(exc_info.value)
        assert "invalid_bad_key" not in str(exc_info.value)

@pytest.mark.asyncio
async def test_groq_rate_limit_and_backoff():
    """Verify HTTP 429 triggers bounded retries before raising GroqRateLimitError."""
    adapter = GroqAdapter(api_key="mock_key", base_url="https://api.groq.com/openai/v1")
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"Retry-After": "0.01"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_post.return_value = mock_resp_429

        with pytest.raises(GroqRateLimitError) as exc_info:
            await adapter.generate("Test prompt")

        assert "rate limit exceeded" in str(exc_info.value)
        # Should attempt 3 times
        assert mock_post.call_count == 3
        # Should back off twice
        assert mock_sleep.call_count == 2

@pytest.mark.asyncio
async def test_groq_timeout_handling():
    """Verify timeout triggers bounded retries before raising GroqTimeoutError."""
    adapter = GroqAdapter(api_key="mock_key", base_url="https://api.groq.com/openai/v1", timeout=5)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")

        with pytest.raises(GroqTimeoutError) as exc_info:
            await adapter.generate("Test prompt")

        assert "timed out" in str(exc_info.value)
        assert mock_post.call_count == 3

@pytest.mark.asyncio
async def test_provider_selection_switching():
    """Verify factory returns GroqAdapter or OllamaAdapter based on AI_PROVIDER."""
    reset_cached_gateway()

    # Test 1: AI_PROVIDER=groq returns GroqAdapter
    with patch.object(settings, "AI_PROVIDER", "groq"), \
         patch.object(settings, "GROQ_API_KEY", "mock_key"), \
         patch("app.ai.groq_adapter.GroqAdapter.is_available", new_callable=AsyncMock) as mock_groq_avail:
        mock_groq_avail.return_value = True
        gw = await get_ai_gateway(force_mock=False)
        assert isinstance(gw, GroqAdapter)

    reset_cached_gateway()

    # Test 2: AI_PROVIDER=ollama returns OllamaAdapter
    with patch.object(settings, "AI_PROVIDER", "ollama"), \
         patch("app.ai.ollama_adapter.OllamaAdapter.is_available", new_callable=AsyncMock) as mock_ollama_avail:
        mock_ollama_avail.return_value = True
        gw = await get_ai_gateway(force_mock=False)
        assert isinstance(gw, OllamaAdapter)

    reset_cached_gateway()

    # Test 3: force_mock=True always returns OfflineMockAdapter
    gw_mock = await get_ai_gateway(force_mock=True)
    assert isinstance(gw_mock, OfflineMockAdapter)

@pytest.mark.asyncio
async def test_groq_strict_non_mocking_on_failure():
    """Verify that when AI_PROVIDER=groq, failures are raised rather than falling back to mock."""
    reset_cached_gateway()

    with patch.object(settings, "AI_PROVIDER", "groq"), \
         patch.object(settings, "USE_OFFLINE_MOCK_IF_OLLAMA_DOWN", True), \
         patch.object(settings, "GROQ_API_KEY", "bad_key"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        gw = await get_ai_gateway(force_mock=False)
        assert isinstance(gw, GroqAdapter)

        # Generating with Groq must raise GroqAuthError, never OfflineMockAdapter
        with pytest.raises(GroqAuthError):
            await gw.generate("Test prompt")

