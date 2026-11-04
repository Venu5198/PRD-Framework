import httpx
import json
import logging
from typing import Optional, Dict, Any, List
from app.ai.gateway import AIGatewayInterface
from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaAdapter(AIGatewayInterface):
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = settings.AI_TIMEOUT_SECONDS

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
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
        temperature: float = 0.2
    ) -> str:
        target_model = model or settings.DEFAULT_MODEL
        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
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
                return data.get("response", "")
            except httpx.HTTPError as err:
                logger.error(f"Ollama generation failed: {err}")
                raise RuntimeError(f"Ollama generation error: {err}") from err

