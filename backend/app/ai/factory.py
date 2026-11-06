import logging
import asyncio
from typing import Optional
from app.ai.gateway import AIGatewayInterface
from app.ai.ollama_adapter import OllamaAdapter
from app.ai.offline_adapter import OfflineMockAdapter
from app.ai.groq_adapter import GroqAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)

_cached_gateway: Optional[AIGatewayInterface] = None

def reset_cached_gateway() -> None:
    """Clear cached AI gateway (used for provider switching and unit tests)."""
    global _cached_gateway
    _cached_gateway = None

async def get_ai_gateway(force_mock: bool = False) -> AIGatewayInterface:
    """
    Factory function returning the configured AI Gateway.
    Configurable via AI_PROVIDER:
    - 'groq': Uses GroqAdapter (no silent fallback to mock or Ollama)
    - 'ollama': Uses OllamaAdapter (with optional offline mock fallback if enabled)
    """
    global _cached_gateway
    if force_mock:
        return OfflineMockAdapter()

    provider = settings.AI_PROVIDER.lower()

    if provider == "groq":
        if _cached_gateway is not None and isinstance(_cached_gateway, GroqAdapter):
            return _cached_gateway

        groq_adapter = GroqAdapter()
        try:
            # 3.0s probe to verify connectivity and model availability
            is_avail = await asyncio.wait_for(groq_adapter.is_available(), timeout=3.0)
            if is_avail:
                _cached_gateway = groq_adapter
                return _cached_gateway
            logger.warning("[AIFactory] Groq is_available probe returned False.")
        except Exception as e:
            logger.warning(f"[AIFactory] Groq probe encountered exception: {e}")

        # When AI_PROVIDER=groq is configured, return the Groq adapter directly
        # to ensure real errors (auth, quota, timeout) are reported rather than masked.
        _cached_gateway = groq_adapter
        return _cached_gateway

    # Default to Ollama
    if _cached_gateway is not None and isinstance(_cached_gateway, OllamaAdapter):
        return _cached_gateway

    ollama = OllamaAdapter()
    try:
        # 600ms fast probe to avoid holding up requests if daemon not running
        is_avail = await asyncio.wait_for(ollama.is_available(), timeout=0.6)
        if is_avail:
            _cached_gateway = ollama
            return _cached_gateway
    except Exception:
        pass

    if settings.USE_OFFLINE_MOCK_IF_OLLAMA_DOWN:
        logger.info("Using deterministic local OfflineMockAdapter (Ollama not connected).")
        _cached_gateway = OfflineMockAdapter()
        return _cached_gateway

    _cached_gateway = ollama
    return _cached_gateway
