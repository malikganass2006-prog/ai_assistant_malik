"""Memory route"""
from fastapi import APIRouter
from models.schemas import MemoryRequest, MemoryResponse
from services.memory_service import memory_service

router = APIRouter()

@router.post("/", response_model=MemoryResponse)
async def manage_memory(request: MemoryRequest):
    if request.action == "get":
        history = await memory_service.get_history(request.session_id)
        return MemoryResponse(session_id=request.session_id, history=history, total_messages=len(history))
    elif request.action == "clear":
        await memory_service.clear_session(request.session_id)
        return MemoryResponse(session_id=request.session_id, history=[], total_messages=0)
    elif request.action == "export":
        data = await memory_service.export_session(request.session_id)
        return MemoryResponse(
            session_id=request.session_id,
            history=data["history"],
            total_messages=data["total_messages"]
        )
    return MemoryResponse(session_id=request.session_id)

@router.get("/sessions")
async def get_sessions():
    return {"sessions": memory_service.get_all_sessions()}
