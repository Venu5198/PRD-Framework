from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class AIGatewayInterface(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2
    ) -> str:
        """Generate text from local AI model."""
        pass

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available local models."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if AI provider is reachable."""
        pass
