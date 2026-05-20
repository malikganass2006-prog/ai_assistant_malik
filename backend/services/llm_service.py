"""
LLM Service - Handles AI reasoning with Groq/OpenAI
Supports streaming and multimodal context fusion
"""

import logging
import asyncio
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx

from config import settings

logger = logging.getLogger("malik.llm_service")


class LLMService:
    """Handles LLM communication with Groq or OpenAI"""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE

        # API endpoints
        self.endpoints = {
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "openai": "https://api.openai.com/v1/chat/completions",
        }

        self.api_keys = {
            "groq": settings.GROQ_API_KEY,
            "openai": settings.OPENAI_API_KEY,
        }

    def _build_multimodal_prompt(self, context: Dict[str, Any]) -> str:
        """Build a rich multimodal prompt from context object"""
        parts = []

        if context.get("user_input"):
            parts.append(f"User message: {context['user_input']}")

        if context.get("speech_text") and context["speech_text"] != context.get("user_input"):
            parts.append(f"Voice transcription: {context['speech_text']}")

        if context.get("image_analysis"):
            parts.append(f"\n[Image Analysis]\n{context['image_analysis']}")

        if context.get("intent"):
            parts.append(f"Detected intent: {context['intent']}")

        return "\n".join(parts) if parts else context.get("user_input", "Hello")

    def _format_history(self, history: List[Dict]) -> List[Dict]:
        """Format conversation history for LLM"""
        formatted = []
        for msg in history[-20:]:  # Last 20 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"] and content:
                formatted.append({"role": role, "content": content})
        return formatted

    async def generate_response(
        self,
        context: Dict[str, Any],
        stream: bool = False
    ) -> str:
        """Generate AI response from multimodal context"""

        endpoint = self.endpoints.get(self.provider)
        api_key = self.api_keys.get(self.provider)

        if not api_key:
            logger.warning(f"No API key for {self.provider}, using mock response")
            return self._mock_response(context)

        # Build messages
        messages = [{"role": "system", "content": settings.SYSTEM_PROMPT}]

        # Add conversation history
        history = self._format_history(context.get("conversation_history", []))
        messages.extend(history)

        # Add current multimodal prompt
        user_prompt = self._build_multimodal_prompt(context)
        messages.append({"role": "user", "content": user_prompt})

        # Determine model (use vision model if image present)
        model = self.model
        if context.get("image_analysis") and self.provider == "groq":
            model = "llama-3.3-70b-versatile"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": stream,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if stream:
                    return await self._stream_response(client, endpoint, headers, payload)
                else:
                    response = await client.post(endpoint, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error {e.response.status_code}: {e.response.text}")
            return f"I encountered an issue connecting to my reasoning engine. Please check your API key and try again."
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "I'm having trouble processing your request right now. Please try again."

    async def _stream_response(self, client, endpoint, headers, payload) -> str:
        """Handle streaming response and collect full text"""
        full_response = []
        async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            full_response.append(delta["content"])
                    except json.JSONDecodeError:
                        pass
        return "".join(full_response)

    def _mock_response(self, context: Dict[str, Any]) -> str:
        """Mock response when no API key is configured"""
        user_input = context.get("user_input", "")
        has_image = bool(context.get("image_analysis"))
        has_voice = bool(context.get("speech_text"))

        modal_info = []
        if has_image:
            modal_info.append("image")
        if has_voice:
            modal_info.append("voice")

        modal_str = f" (with {' + '.join(modal_info)})" if modal_info else ""

        return (
            f"Hello! I'm Malik, your multimodal AI assistant{modal_str}. "
            f"I received your message: '{user_input}'. "
            f"To enable full AI responses, please configure your GROQ_API_KEY or OPENAI_API_KEY in the .env file. "
            f"I support voice, text, and image input simultaneously!"
        )

    async def detect_intent(self, text: str) -> str:
        """Detect user intent from input text"""
        intents = {
            "question": ["what", "how", "why", "when", "where", "who", "explain", "tell me"],
            "analysis": ["analyze", "compare", "evaluate", "assess", "review"],
            "creation": ["write", "create", "generate", "make", "build", "draft"],
            "translation": ["translate", "urdu", "english", "language"],
            "image_query": ["image", "photo", "picture", "see", "look", "show"],
            "greeting": ["hello", "hi", "hey", "salam", "assalam"],
        }

        text_lower = text.lower()
        for intent, keywords in intents.items():
            if any(kw in text_lower for kw in keywords):
                return intent
        return "general"


# Singleton instance
llm_service = LLMService()
