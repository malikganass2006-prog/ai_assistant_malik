"""
Malik AI Assistant - Main FastAPI Application
Production-grade multimodal AI backend
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

from routes.chat import router as chat_router
from routes.voice import router as voice_router
from routes.vision import router as vision_router
from routes.memory import router as memory_router
from routes.automation import router as automation_router
from routes.agent import router as agent_router
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("malik_assistant.log")
    ]
)
logger = logging.getLogger("malik.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Malik AI Assistant starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    yield
    logger.info("Malik AI Assistant shutting down...")


app = FastAPI(
    title="Malik AI Assistant",
    description="Production-grade Multimodal AI Assistant with Voice, Vision, and Context Intelligence",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(voice_router, prefix="/api/voice", tags=["Voice"])
app.include_router(vision_router, prefix="/api/vision", tags=["Vision"])
app.include_router(memory_router, prefix="/api/memory", tags=["Memory"])
app.include_router(automation_router, prefix="/api/automation", tags=["Desktop Automation"])
app.include_router(agent_router, prefix="/api/agent", tags=["Agent"])

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the main frontend application"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Malik AI Assistant API", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Malik AI Assistant",
        "version": "1.0.0"
    }

@app.get("/api/config")
async def get_config():
    """Get frontend configuration"""
    return {
        "tts_enabled": True,
        "stt_enabled": True,
        "vision_enabled": True,
        "supported_languages": ["en", "ur"],
        "max_image_size_mb": 10,
        "models": {
            "llm": settings.LLM_MODEL,
            "vision": "vision-capable"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
