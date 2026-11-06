from fastapi import APIRouter
from app.core.config import settings
from app.ai.factory import get_ai_gateway
from app.core.database import db_manager

router = APIRouter()

@router.get("/health")
async def health_check():
    ai_gw = await get_ai_gateway()
    ai_available = await ai_gw.is_available()
    active_model = settings.GROQ_MODEL if settings.AI_PROVIDER == "groq" else settings.DEFAULT_MODEL
    
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "database": {
            "connected": db_manager.db is not None,
            "is_in_memory_mock": db_manager.is_mock
        },
        "ai_engine": {
            "provider": settings.AI_PROVIDER,
            "type": ai_gw.__class__.__name__,
            "available": ai_available,
            "default_model": active_model
        }
    }

@router.get("/models")
async def list_models():
    ai_gw = await get_ai_gateway()
    models = await ai_gw.list_models()
    active_model = settings.GROQ_MODEL if settings.AI_PROVIDER == "groq" else settings.DEFAULT_MODEL
    return {
        "provider": settings.AI_PROVIDER,
        "active_model": active_model,
        "available_models": models
    }

@router.post("/models/select")
async def select_model(payload: dict):
    new_model = payload.get("model")
    if not new_model:
        return {"error": "Model name required"}
    if settings.AI_PROVIDER == "groq":
        settings.GROQ_MODEL = new_model
    else:
        settings.DEFAULT_MODEL = new_model
    ai_gw = await get_ai_gateway()
    if hasattr(ai_gw, "model"):
        ai_gw.model = new_model
    active_model = settings.GROQ_MODEL if settings.AI_PROVIDER == "groq" else settings.DEFAULT_MODEL
    return {"status": "success", "active_model": active_model}
