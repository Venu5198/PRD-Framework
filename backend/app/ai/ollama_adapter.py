import httpx
import json
import logging
from typing import Optional, Dict, Any, List
from app.ai.gateway import AIGatewayInterface
from app.ai.exceptions import (
    OllamaUnavailableError,
    OllamaTimeoutError,
    OllamaGenerationError,
    InvalidModelResponseError
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaAdapter(AIGatewayInterface):
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.AI_TIMEOUT_SECONDS

    async def is_available(self, require_model: bool = True) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code != 200:
                    return False
                if require_model:
                    data = res.json()
                    models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                    target = settings.DEFAULT_MODEL.split(":")[0]
                    return target in models
                return True
        except Exception:
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = data.get("models", [])
                    return [{"name": m.get("name"), "size": m.get("size"), "modified_at": m.get("modified_at")} for m in models]
        except Exception as e:
            logger.warning(f"Error fetching Ollama models: {e}")
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
        target_model = model or settings.DEFAULT_MODEL
        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 1024
            }
        }
        if system_instruction:
            payload["system"] = system_instruction
        if json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                res.raise_for_status()
                data = res.json()
                response_text = data.get("response", "")
                if not response_text and not json_mode:
                    raise InvalidModelResponseError("Ollama returned an empty response string.")
                return response_text
            except httpx.TimeoutException as err:
                logger.error(f"Ollama generation timed out after {self.timeout}s: {err}")
                if allow_fallback and settings.USE_OFFLINE_MOCK_IF_OLLAMA_DOWN:
                    logger.warning("Explicit fallback allowed: invoking OfflineMockAdapter.")
                    from app.ai.offline_adapter import OfflineMockAdapter
                    mock_adapter = OfflineMockAdapter()
                    return await mock_adapter.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        model=model,
                        json_mode=json_mode,
                        temperature=temperature
                    )
                raise OllamaTimeoutError(f"Inference timed out after {self.timeout} seconds.") from err
            except httpx.ConnectError as err:
                logger.error(f"Cannot connect to Ollama at {self.base_url}: {err}")
                if allow_fallback and settings.USE_OFFLINE_MOCK_IF_OLLAMA_DOWN:
                    logger.warning("Explicit fallback allowed: invoking OfflineMockAdapter.")
                    from app.ai.offline_adapter import OfflineMockAdapter
                    mock_adapter = OfflineMockAdapter()
                    return await mock_adapter.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        model=model,
                        json_mode=json_mode,
                        temperature=temperature
                    )
                raise OllamaUnavailableError(f"Ollama server at {self.base_url} is unreachable.") from err
            except httpx.HTTPError as err:
                logger.error(f"Ollama generation HTTP error: {err}")
                if allow_fallback and settings.USE_OFFLINE_MOCK_IF_OLLAMA_DOWN:
                    logger.warning("Explicit fallback allowed: invoking OfflineMockAdapter.")
                    from app.ai.offline_adapter import OfflineMockAdapter
                    mock_adapter = OfflineMockAdapter()
                    return await mock_adapter.generate(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        model=model,
                        json_mode=json_mode,
                        temperature=temperature
                    )
                raise OllamaGenerationError(f"Ollama generation failed: {err}") from err
