"""
Chat Router - Main conversation and multimodal fusion endpoint
"""

import asyncio
import logging
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json

from backend.models.schemas import ChatRequest, ChatResponse, MultimodalContext
from backend.services.llm_service import llm_service
from backend.services.vision_service import vision_service
from backend.services.tts_service import tts_service
from backend.services.memory_service import memory_service

logger = logging.getLogger("malik.chat_router")
router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def process_message(request: ChatRequest):
    """
    Main multimodal message processing endpoint.
    Fuses text, voice, and image inputs into a coherent AI response.
    """
    start_time = time.time()
    session_id = request.session_id

    try:
        logger.info(f"Processing message for session {session_id[:8]}... "
                   f"[text={bool(request.message)}, speech={bool(request.speech_text)}, "
                   f"image={bool(request.image_base64)}]")

        combined_text = request.message or request.speech_text or ""

        # Step 1: Load history, detect intent, and analyze image concurrently when possible.
        tasks = [
            memory_service.get_context_window(session_id),
            llm_service.detect_intent(combined_text),
        ]
        if request.image_base64:
            logger.info("Analyzing image...")
            tasks.append(vision_service.analyze_image(
                request.image_base64,
                query=combined_text or "Describe this image"
            ))

        results = await asyncio.gather(*tasks)
        conversation_history = results[0]
        intent = results[1]

        image_analysis = ""
        if request.image_base64:
            vision_result = results[2]
            image_analysis = vision_result.get("description", "")
            if vision_result.get("objects"):
                image_analysis += f"\n\nDetected objects: {', '.join(vision_result['objects'])}"
            if vision_result.get("text_content"):
                image_analysis += f"\n\nVisible text: {vision_result['text_content']}"

        # Step 4: Build multimodal context object
        context = {
            "user_input": request.message,
            "speech_text": request.speech_text,
            "image_analysis": image_analysis,
            "conversation_history": conversation_history,
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "language": request.language,
        }

        logger.info(f"Multimodal context built: intent={intent}, "
                   f"has_image={bool(image_analysis)}, "
                   f"history_len={len(conversation_history)}")

        # Step 5: Generate AI response
        ai_response = await llm_service.generate_response(context)

        # Step 6: Save to memory
        user_message = request.message or request.speech_text or "[voice/image input]"
        await memory_service.add_message(
            session_id, "user", user_message,
            metadata={"has_image": bool(request.image_base64), "intent": intent}
        )
        await memory_service.add_message(session_id, "assistant", ai_response)

        # Step 7: Generate TTS if requested
        audio_b64 = None
        if request.voice_enabled and ai_response:
            logger.info("Generating TTS audio...")
            audio_b64 = await tts_service.synthesize(ai_response, request.language)

        processing_time = time.time() - start_time
        logger.info(f"Request processed in {processing_time:.2f}s")

        return ChatResponse(
            response=ai_response,
            audio_base64=audio_b64,
            session_id=session_id,
            processing_time=processing_time,
            multimodal_context={
                "has_image": bool(image_analysis),
                "has_voice": bool(request.speech_text),
                "intent": intent,
                "history_length": len(conversation_history),
            },
            status="success"
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_message(request: ChatRequest):
    """Stream AI response tokens in real-time"""

    async def generate():
        session_id = request.session_id
        start_time = time.time()
        combined_text = request.message or request.speech_text or ""

        # Process history, intent, and image concurrently
        tasks = [
            memory_service.get_context_window(session_id),
            llm_service.detect_intent(combined_text),
        ]
        if request.image_base64:
            logger.info("Analyzing image for stream...")
            tasks.append(vision_service.analyze_image(
                request.image_base64,
                query=combined_text or "Describe this image"
            ))

        results = await asyncio.gather(*tasks)
        conversation_history = results[0]
        intent = results[1]

        image_analysis = ""
        if request.image_base64:
            vision_result = results[2]
            image_analysis = vision_result.get("description", "")
            if vision_result.get("objects"):
                image_analysis += f"\n\nDetected objects: {', '.join(vision_result['objects'])}"
            if vision_result.get("text_content"):
                image_analysis += f"\n\nVisible text: {vision_result['text_content']}"

        context = {
            "user_input": request.message,
            "speech_text": request.speech_text,
            "image_analysis": image_analysis,
            "conversation_history": conversation_history,
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "language": request.language,
        }

        user_msg = request.message or request.speech_text or "[input]"
        await memory_service.add_message(session_id, "user", user_msg)

        assistant_text = ""
        async for chunk in llm_service.stream_response(context):
            if chunk.get("text"):
                assistant_text += chunk["text"]
            yield f"data: {json.dumps(chunk)}\n\n"

        processing_time = time.time() - start_time
        await memory_service.add_message(session_id, "assistant", assistant_text)
        yield f"data: {json.dumps({'done': True, 'processing_time': processing_time, 'intent': intent, 'has_image': bool(image_analysis)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
