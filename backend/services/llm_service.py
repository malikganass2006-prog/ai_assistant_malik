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

        if not api_key or self.provider == "offline":
            if settings.OFFLINE_MODE:
                logger.info("Using offline response engine")
                return self._offline_response(context)
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

    async def stream_response(self, context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream partial assistant response tokens as they arrive."""
        endpoint = self.endpoints.get(self.provider)
        api_key = self.api_keys.get(self.provider)

        if not api_key or self.provider == "offline":
            if settings.OFFLINE_MODE:
                text = self._offline_response(context)
            else:
                text = self._mock_response(context)
            yield {"text": text, "done": True}
            return

        messages = [{"role": "system", "content": settings.SYSTEM_PROMPT}]
        history = self._format_history(context.get("conversation_history", []))
        messages.extend(history)
        user_prompt = self._build_multimodal_prompt(context)
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield {"text": delta["content"], "done": False}
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error {e.response.status_code}: {e.response.text}")
            yield {"text": "I encountered an issue connecting to my reasoning engine. Please check your API key and try again.", "done": True}
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            yield {"text": "I'm having trouble processing your request right now. Please try again.", "done": True}

    def _offline_response(self, context: Dict[str, Any]) -> str:
        """Generate a simple offline assistant answer when no cloud API is available."""
        text = (context.get("user_input") or "").strip()
        if not text:
            return "Hello! I'm Malik in offline mode. Ask me anything or describe a desktop automation task."

        lower = text.lower()
        if any(kw in lower for kw in ["hello", "hi", "salam", "hey"]):
            return "Hi there! I'm Malik in offline mode. I can help with local desktop automation tasks and simple guidance."
        if any(kw in lower for kw in ["thanks", "thank you"]):
            return "You're welcome! Let me know if you need anything else."
        if any(kw in lower for kw in ["how are you", "what's up", "how is it going"]):
            return "I'm ready to help in offline mode. Tell me what you want to do on your computer."
        if any(kw in lower for kw in ["list files", "list directory", "show files", "open folder", "read file", "run command", "open url"]):
            return (
                "I can help with desktop automation. Use the dedicated automation endpoint at `/api/automation` or the agent endpoint `/api/agent/execute` "
                "to run commands, list directories, read files, open URLs, or open local paths."
            )
        if any(kw in lower for kw in ["bye", "goodbye", "see you"]):
            return "Goodbye! Feel free to return whenever you need help with local automation or offline assistance."

        return (
            "I'm operating in offline mode, so my ability to generate complex responses is limited. "
            "I can still provide simple guidance and help you trigger local tasks. "
            "Please try asking for a local desktop action, or configure a cloud API key for full AI capability."
        )

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
