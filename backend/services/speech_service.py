"""
Speech Service - Speech-to-Text processing
Supports Web Speech API (frontend) and Whisper (backend)
"""

import logging
import base64
import io
import asyncio
from typing import Optional
import httpx

from config import settings

logger = logging.getLogger("malik.speech_service")


class SpeechService:
    """Handles speech-to-text conversion"""

    def __init__(self):
        self.provider = settings.STT_PROVIDER
        self.openai_key = settings.OPENAI_API_KEY
        self.groq_key = settings.GROQ_API_KEY

    async def transcribe(self, audio_base64: str, language: str = "en") -> Optional[str]:
        """Transcribe audio to text"""
        if not audio_base64:
            return None

        # Decode audio
        if "," in audio_base64:
            audio_base64 = audio_base64.split(",")[1]

        try:
            audio_bytes = base64.b64decode(audio_base64)
        except Exception as e:
            logger.error(f"Failed to decode audio: {e}")
            return None

        try:
            if self.groq_key:
                return await self._groq_whisper(audio_bytes, language)
            elif self.openai_key:
                return await self._openai_whisper(audio_bytes, language)
            else:
                logger.warning("No STT API key configured - using Web Speech API on frontend")
                return None
        except Exception as e:
            logger.error(f"STT error: {e}")
            return None

    async def _groq_whisper(self, audio_bytes: bytes, language: str = "en") -> Optional[str]:
        """Use Groq's Whisper endpoint for fast transcription"""
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.groq_key}"}

        lang_map = {"en": "en", "ur": "ur"}
        lang = lang_map.get(language, "en")

        files = {"file": ("audio.webm", audio_bytes, "audio/webm")}
        data = {"model": "whisper-large-v3", "language": lang}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            return response.json().get("text", "")

    async def _openai_whisper(self, audio_bytes: bytes, language: str = "en") -> Optional[str]:
        """Use OpenAI Whisper for transcription"""
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.openai_key}"}

        files = {"file": ("audio.webm", audio_bytes, "audio/webm")}
        data = {"model": "whisper-1", "language": language}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            return response.json().get("text", "")

    async def normalize_text(self, text: str) -> str:
        """Normalize and clean transcribed text"""
        if not text:
            return ""

        # Basic normalization
        text = text.strip()
        if text and not text[-1] in ".!?":
            text += "."
        return text


# Singleton instance
speech_service = SpeechService()
