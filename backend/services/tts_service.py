"""
TTS Service - Text-to-Speech generation
Supports gTTS (free) and ElevenLabs (premium)
"""

import logging
import base64
import io
import asyncio
from typing import Optional
import httpx

from config import settings

logger = logging.getLogger("malik.tts_service")


class TTSService:
    """Text-to-Speech service with multiple provider support"""

    def __init__(self):
        self.provider = settings.TTS_PROVIDER
        self.language = settings.TTS_LANGUAGE
        self.elevenlabs_key = settings.ELEVENLABS_API_KEY
        self.elevenlabs_voice_id = settings.ELEVENLABS_VOICE_ID

    async def synthesize(self, text: str, language: str = "en") -> Optional[str]:
        """Convert text to speech, return base64-encoded audio"""
        if not text or not text.strip():
            return None

        # Truncate very long text for TTS
        if len(text) > 1000:
            text = text[:1000] + "..."

        try:
            if self.provider == "elevenlabs" and self.elevenlabs_key:
                return await self._elevenlabs_tts(text)
            else:
                return await self._gtts_synthesize(text, language)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            # Fallback to gTTS
            try:
                return await self._gtts_synthesize(text, language)
            except Exception as e2:
                logger.error(f"TTS fallback error: {e2}")
                return None

    async def _gtts_synthesize(self, text: str, language: str = "en") -> Optional[str]:
        """Generate speech using gTTS"""
        try:
            from gtts import gTTS
            import tempfile

            # Map language codes
            lang_map = {"en": "en", "ur": "ur"}
            lang = lang_map.get(language, "en")

            loop = asyncio.get_event_loop()

            def _generate():
                tts = gTTS(text=text, lang=lang, slow=False)
                buffer = io.BytesIO()
                tts.write_to_fp(buffer)
                buffer.seek(0)
                return buffer.read()

            audio_bytes = await loop.run_in_executor(None, _generate)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            logger.info(f"Generated gTTS audio: {len(audio_bytes)} bytes")
            return audio_b64

        except ImportError:
            logger.warning("gTTS not installed. Run: pip install gtts")
            return None
        except Exception as e:
            logger.error(f"gTTS error: {e}")
            return None

    async def _elevenlabs_tts(self, text: str) -> Optional[str]:
        """Generate speech using ElevenLabs API"""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key,
        }

        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            audio_b64 = base64.b64encode(response.content).decode("utf-8")
            logger.info(f"Generated ElevenLabs audio: {len(response.content)} bytes")
            return audio_b64

    def estimate_duration(self, text: str) -> float:
        """Estimate speech duration in seconds"""
        words = len(text.split())
        return max(1.0, words / 2.5)  # ~150 words/min average


# Singleton instance
tts_service = TTSService()
