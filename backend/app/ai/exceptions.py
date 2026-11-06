class AIError(Exception):
    """Base exception for AI engine errors."""
    def __init__(self, message: str, code: str = "AI_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

class OllamaUnavailableError(AIError):
    def __init__(self, message: str = "Ollama service is not reachable or unavailable."):
        super().__init__(message, code="OLLAMA_UNAVAILABLE")

class OllamaTimeoutError(AIError):
    def __init__(self, message: str = "Ollama inference timed out."):
        super().__init__(message, code="OLLAMA_TIMEOUT")

class OllamaGenerationError(AIError):
    def __init__(self, message: str):
        super().__init__(message, code="OLLAMA_GENERATION_FAILED")

class InvalidModelResponseError(AIError):
    def __init__(self, message: str = "Model returned invalid or unparseable response."):
        super().__init__(message, code="INVALID_MODEL_RESPONSE")

class GroqAuthError(AIError):
    def __init__(self, message: str = "Groq authentication failed. Please verify GROQ_API_KEY."):
        super().__init__(message, code="GROQ_AUTH_FAILED")

class GroqRateLimitError(AIError):
    def __init__(self, message: str = "Groq API rate limit exceeded."):
        super().__init__(message, code="GROQ_RATE_LIMIT")

class GroqTimeoutError(AIError):
    def __init__(self, message: str = "Groq API request timed out."):
        super().__init__(message, code="GROQ_TIMEOUT")

class GroqGenerationError(AIError):
    def __init__(self, message: str):
        super().__init__(message, code="GROQ_GENERATION_FAILED")

class GroqModelUnavailableError(AIError):
    def __init__(self, message: str):
        super().__init__(message, code="GROQ_MODEL_UNAVAILABLE")
