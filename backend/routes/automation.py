"""Automation route for local desktop actions."""

from fastapi import APIRouter, HTTPException

from models.schemas import DesktopRequest, DesktopResponse
from services.desktop_service import desktop_service

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
        elif request.action == "open_application":
            result = await desktop_service.open_application(request.app_name or "", request.path or "")
        elif request.action == "close_application":
            result = await desktop_service.close_application(request.process_name or "")
        elif request.action == "browser_automation":
            result = await desktop_service.browser_automation(request.browser_action or "open", request.url or "")
        elif request.action == "mouse_control":
            result = await desktop_service.mouse_control(
                request.mouse_action or "click",
                request.x,
                request.y,
                request.button or "left",
                request.clicks or 1,
            )
        elif request.action == "keyboard_control":
            result = await desktop_service.keyboard_control(request.keyboard_action or "type", request.keys or "")
        elif request.action == "window_management":
            result = await desktop_service.manage_window(request.window_action or "activate", request.window_title)
        else:
            return DesktopResponse(status="error", output="Unsupported action.")

        return DesktopResponse(
            status=result.get("status", "error"),
            output=result.get("stdout", result.get("content", result.get("message", ""))),
            details=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
