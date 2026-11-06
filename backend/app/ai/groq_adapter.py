import asyncio
import httpx
import json
import logging
import time
from typing import Optional, Dict, Any, List
from app.ai.gateway import AIGatewayInterface
from app.ai.exceptions import (
    GroqAuthError,
    GroqRateLimitError,
    GroqTimeoutError,
    GroqGenerationError,
    GroqModelUnavailableError,
    InvalidModelResponseError
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class GroqAdapter(AIGatewayInterface):
    """
    OpenAI-compatible Groq LPU AI Adapter.
    Executes fast inference using Groq's API while preserving strict security
    (zero key logging), structured JSON validation, and bounded exponential backoff.
    """
    DEFAULT_USER_AGENT = "PRD-Framework/1.0"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.base_url = (base_url or settings.GROQ_BASE_URL).rstrip("/")
        self.model = model or settings.GROQ_MODEL
        self.timeout = timeout or settings.AI_TIMEOUT_SECONDS

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise GroqAuthError("GROQ_API_KEY is not configured in backend environment variables.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": self.DEFAULT_USER_AGENT
        }

    async def is_available(self, require_model: bool = True) -> bool:
        """Check if Groq API is reachable and optionally verify the selected model."""
        if not self.api_key:
            logger.warning("[GroqAdapter] Availability check failed: GROQ_API_KEY missing.")
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=self._get_headers())
                if res.status_code != 200:
                    logger.warning(f"[GroqAdapter] Availability check returned HTTP {res.status_code}")
                    return False
                if require_model:
                    data = res.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    target = self.model or settings.GROQ_MODEL
                    return target in models
                return True
        except Exception as e:
            logger.warning(f"[GroqAdapter] Reachability probe failed: {type(e).__name__}")
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available Groq models."""
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    return [
                        {
                            "name": m.get("id"),
                            "owned_by": m.get("owned_by"),
                            "created": m.get("created"),
                            "active": m.get("active", True)
                        }
                        for m in data.get("data", [])
                    ]
        except Exception as e:
            logger.warning(f"[GroqAdapter] Error listing models: {type(e).__name__}")
        return []

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        allow_fallback: bool = False
    ) -> str:
        """
        Generate completion from Groq API with bounded retries, latency logging,
        and structured JSON validation.
        """
        if not self.api_key:
            raise GroqAuthError("GROQ_API_KEY is not configured in backend environment variables.")

        target_model = model or self.model or settings.GROQ_MODEL
        messages: List[Dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = self._get_headers()
        max_retries = 3
        backoff_delays = [1.0, 2.0, 4.0]

        for attempt in range(max_retries):
            start_time = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers
                    )
                    latency_ms = int((time.perf_counter() - start_time) * 1000)

                    # Handle Authentication & Authorization errors
                    if res.status_code in (401, 403):
                        logger.error(
                            f"[GroqAdapter] Auth failure: HTTP {res.status_code} "
                            f"(provider=groq, model={target_model}, latency_ms={latency_ms})"
                        )
                        raise GroqAuthError(f"Groq authentication rejected with HTTP {res.status_code}.")

                    # Handle Rate Limiting (429)
                    if res.status_code == 429:
                        retry_after_str = res.headers.get("Retry-After")
                        retry_after = float(retry_after_str) if retry_after_str else backoff_delays[min(attempt, len(backoff_delays)-1)]
                        logger.warning(
                            f"[GroqAdapter] Rate limited (attempt {attempt+1}/{max_retries}): "
                            f"HTTP 429, waiting {retry_after:.1f}s (provider=groq, model={target_model})"
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        raise GroqRateLimitError(f"Groq rate limit exceeded after {max_retries} attempts.")

                    # Handle Server Errors (500, 502, 503, 504)
                    if res.status_code >= 500:
                        logger.warning(
                            f"[GroqAdapter] Server error (attempt {attempt+1}/{max_retries}): "
                            f"HTTP {res.status_code} (provider=groq, model={target_model})"
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(backoff_delays[attempt])
                            continue
                        raise GroqGenerationError(f"Groq service unavailable: HTTP {res.status_code}")

                    # Handle Client Errors (400, etc.)
                    if res.status_code == 400:
                        logger.error(
                            f"[GroqAdapter] HTTP 400 Bad Request from Groq: {res.text} "
                            f"(provider=groq, model={target_model})"
                        )
                        raise GroqGenerationError(f"Groq bad request (HTTP 400): {res.text}")

                    # Raise for any remaining 4xx client errors
                    res.raise_for_status()

                    data = res.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise InvalidModelResponseError("Groq returned response without choices.")

                    first_choice = choices[0]
                    message = first_choice.get("message", {})
                    response_text = message.get("content", "")

                    if not response_text and not json_mode:
                        raise InvalidModelResponseError("Groq returned empty response content.")

                    if json_mode:
                        try:
                            # Verify valid JSON syntax
                            json.loads(response_text)
                        except (json.JSONDecodeError, TypeError) as json_err:
                            raise InvalidModelResponseError(
                                f"Groq response violated json_mode contract: {json_err}"
                            ) from json_err

                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    logger.info(
                        f"[GroqAdapter] Successful generation: provider=groq, model={target_model}, "
                        f"latency_ms={latency_ms}, prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}"
                    )
                    return response_text

            except httpx.TimeoutException as timeout_err:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                logger.warning(
                    f"[GroqAdapter] Request timed out (attempt {attempt+1}/{max_retries}): "
                    f"provider=groq, model={target_model}, latency_ms={latency_ms}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff_delays[attempt])
                    continue
                raise GroqTimeoutError(f"Groq inference timed out after {self.timeout} seconds.") from timeout_err

            except httpx.RequestError as req_err:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                logger.warning(
                    f"[GroqAdapter] Network error (attempt {attempt+1}/{max_retries}): "
                    f"provider=groq, model={target_model}, error={type(req_err).__name__}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff_delays[attempt])
                    continue
                raise GroqGenerationError(f"Groq network connection failed: {req_err}") from req_err

        raise GroqGenerationError(f"Groq generation failed after {max_retries} attempts.")
