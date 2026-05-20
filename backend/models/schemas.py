"""
Pydantic models for Malik AI Assistant
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    has_image: bool = False
    image_analysis: Optional[str] = None


class MultimodalContext(BaseModel):
    """Core multimodal context object sent to LLM"""
    user_input: str = ""
    speech_text: str = ""
    image_analysis: str = ""
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    intent: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    language: str = "en"


class ChatRequest(BaseModel):
    message: str = ""
    speech_text: str = ""
    image_base64: Optional[str] = None
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    language: str = "en"
    voice_enabled: bool = True


class ChatResponse(BaseModel):
    response: str
    audio_base64: Optional[str] = None
    session_id: str
    processing_time: float
    multimodal_context: Optional[Dict[str, Any]] = None
    status: str = "success"


class VoiceRequest(BaseModel):
    text: str
    language: str = "en"
    voice_id: Optional[str] = None


class VoiceResponse(BaseModel):
    audio_base64: str
    duration_estimate: float
    status: str = "success"


class VisionRequest(BaseModel):
    image_base64: str
    query: str = ""


class VisionResponse(BaseModel):
    description: str
    objects: List[str] = Field(default_factory=list)
    text_content: str = ""
    scene: str = ""
    status: str = "success"


class MemoryRequest(BaseModel):
    session_id: str
    action: str  # "get", "clear", "export"


class MemoryResponse(BaseModel):
    session_id: str
    history: List[Dict[str, Any]] = Field(default_factory=list)
    total_messages: int = 0
    status: str = "success"
