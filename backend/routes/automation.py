"""Automation route for local desktop actions."""

from fastapi import APIRouter, HTTPException

from backend.models.schemas import DesktopRequest, DesktopResponse
from backend.services.desktop_service import desktop_service

router = APIRouter()

@router.post("/desktop", response_model=DesktopResponse)
async def desktop_action(request: DesktopRequest):
    try:
        if request.action == "run_command":
            result = await desktop_service.run_command(request.command or "")
        elif request.action == "list_directory":
            result = await desktop_service.list_directory(request.path or ".")
        elif request.action == "read_file":
            result = await desktop_service.read_file(request.path or "")
        elif request.action == "open_url":
            result = await desktop_service.open_url(request.url or "")
        elif request.action == "open_path":
            result = await desktop_service.open_path(request.path or "")
        else:
            return DesktopResponse(status="error", output="Unsupported action.")

        return DesktopResponse(
            status=result.get("status", "error"),
            output=result.get("stdout", result.get("content", result.get("message", ""))),
            details=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
