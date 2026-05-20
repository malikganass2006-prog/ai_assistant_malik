"""Autonomous agent router for executing local desktop tasks."""

import logging
from fastapi import APIRouter, HTTPException

from models.schemas import AgentRequest, AgentResponse
from services.agent_service import agent_service

logger = logging.getLogger("malik.agent_router")
router = APIRouter()

@router.post("/execute", response_model=AgentResponse)
async def execute_agent(request: AgentRequest):
    try:
        logger.info(f"Agent execution request: {request.instruction[:128]}")
        result = await agent_service.execute_instruction(request.instruction, request.session_id)
        return AgentResponse(
            status=result.get("status", "error"),
            plan=result.get("plan", []),
            results=result.get("results", []),
            summary=result.get("summary", "")
        )
    except Exception as e:
        logger.error(f"Agent execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
