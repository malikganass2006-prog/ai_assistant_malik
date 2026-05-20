"""Vision route"""
from fastapi import APIRouter
from backend.models.schemas import VisionRequest, VisionResponse
from backend.services.vision_service import vision_service

router = APIRouter()

@router.post("/analyze", response_model=VisionResponse)
async def analyze_image(request: VisionRequest):
    result = await vision_service.analyze_image(request.image_base64, request.query)
    return VisionResponse(
        description=result.get("description", ""),
        objects=result.get("objects", []),
        text_content=result.get("text_content", ""),
        scene=result.get("scene", ""),
        status="success"
    )
