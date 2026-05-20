"""Voice route"""
from fastapi import APIRouter
from backend.models.schemas import VoiceRequest, VoiceResponse
from backend.services.tts_service import tts_service

router = APIRouter()

@router.post("/synthesize", response_model=VoiceResponse)
async def synthesize_speech(request: VoiceRequest):
    audio_b64 = await tts_service.synthesize(request.text, request.language)
    duration = tts_service.estimate_duration(request.text)
    return VoiceResponse(
        audio_base64=audio_b64 or "",
        duration_estimate=duration,
        status="success" if audio_b64 else "no_audio"
    )
