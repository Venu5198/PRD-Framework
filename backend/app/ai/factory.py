import logging
import asyncio
from typing import Optional
from app.ai.gateway import AIGatewayInterface
from app.ai.ollama_adapter import OllamaAdapter
from app.ai.offline_adapter import OfflineMockAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)

_cached_gateway: Optional[AIGatewayInterface] = None

async def get_ai_gateway(force_mock: bool = False) -> AIGatewayInterface:
    global _cached_gateway
    if force_mock:
        return OfflineMockAdapter()

    if _cached_gateway is not None:
        return _cached_gateway

    ollama = OllamaAdapter()
    try:
        # 500ms fast probe to avoid holding up requests if daemon not running
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
