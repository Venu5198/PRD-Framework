from fastapi import APIRouter
from app.core.config import settings
from app.ai.factory import get_ai_gateway
from app.core.database import db_manager

router = APIRouter()

@router.get("/health")
async def health_check():
    ai_gw = await get_ai_gateway()
    ai_available = await ai_gw.is_available()
    
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "database": {
            "connected": db_manager.db is not None,
            "is_in_memory_mock": db_manager.is_mock
        },
        "ai_engine": {
            "type": ai_gw.__class__.__name__,
            "available": ai_available,
            "default_model": settings.DEFAULT_MODEL
        }
    }

@router.get("/models")
async def list_models():
    ai_gw = await get_ai_gateway()
    models = await ai_gw.list_models()
    return {
        "active_model": settings.DEFAULT_MODEL,
        "available_models": models
    }

@router.post("/models/select")
async def select_model(payload: dict):
    new_model = payload.get("model")
    if not new_model:
        return {"error": "Model name required"}
    settings.DEFAULT_MODEL = new_model
    return {"status": "success", "active_model": settings.DEFAULT_MODEL}

