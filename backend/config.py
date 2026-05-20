"""
Configuration settings for Malik AI Assistant
Uses environment variables with sensible defaults
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    OFFLINE_MODE: bool = os.getenv("OFFLINE_MODE", "true").lower() == "true"
    OFFLINE_MODEL_PATH: str = os.getenv("OFFLINE_MODEL_PATH", "")

    # TTS Configuration
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "gtts")  # gtts or elevenlabs
    TTS_LANGUAGE: str = os.getenv("TTS_LANGUAGE", "en")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    # STT Configuration
    STT_PROVIDER: str = os.getenv("STT_PROVIDER", "webspeech")  # webspeech or whisper
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")

    # Memory Configuration
    MEMORY_TYPE: str = os.getenv("MEMORY_TYPE", "file")  # file or memory
    MEMORY_MAX_HISTORY: int = int(os.getenv("MEMORY_MAX_HISTORY", "50"))
    MEMORY_FILE_PATH: str = os.getenv("MEMORY_FILE_PATH", "conversation_history.json")

    # Vision Configuration
    VISION_PROVIDER: str = os.getenv("VISION_PROVIDER", "groq")

    # System Prompt
    SYSTEM_PROMPT: str = """You are Malik, a friendly digital assistant like Siri.

You understand voice, images, and text input at the same time.
You respond quickly, directly, and politely.
You sound like a virtual assistant: short, helpful, and action-oriented.

Guidelines:
- Use clear, concise, voice-like answers for commands and questions
- Confirm any desktop automation action before performing it when appropriate
- If the user speaks Urdu, respond in Urdu
- Keep replies warm, professional, and easy to understand
- When image context is provided, analyze it and mention relevant details
- Maintain conversation continuity from history while staying brief
- Be honest about capabilities and limitations"""


settings = Settings()
