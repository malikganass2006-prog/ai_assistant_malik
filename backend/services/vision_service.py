"""
Vision Service - Image understanding and analysis
Supports Groq Vision and OpenAI Vision APIs
"""

import logging
import base64
import io
import json
from typing import Dict, Any, Optional
import httpx

from config import settings

logger = logging.getLogger("malik.vision_service")


class VisionService:
    """Handles image analysis and understanding"""

    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        self.openai_key = settings.OPENAI_API_KEY

    async def analyze_image(
        self,
        image_base64: str,
        query: str = "Describe this image in detail"
    ) -> Dict[str, Any]:
        """Analyze an image and return structured description"""

        if not image_base64:
            return self._empty_result()

        # Clean base64 data URL prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        # Detect image format
        media_type = self._detect_media_type(image_base64)

        try:
            if self.openai_key:
                return await self._openai_vision(image_base64, media_type, query)
            elif self.groq_key:
                return await self._groq_vision(image_base64, media_type, query)
            else:
                logger.warning("No vision API key configured")
                return self._mock_vision_result()
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            return {"description": f"Image received but analysis failed: {str(e)}", "objects": [], "scene": "", "text_content": ""}

    async def _openai_vision(self, image_b64: str, media_type: str, query: str) -> Dict[str, Any]:
        """Use OpenAI GPT-4 Vision for image analysis"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }

        prompt = f"""Analyze this image comprehensively. Provide:
1. Detailed scene description
2. Main objects present
3. Any visible text (OCR)
4. Overall context/setting

User query: {query}

Respond in JSON format:
{{
  "description": "...",
  "objects": ["obj1", "obj2"],
  "text_content": "any text visible in image",
  "scene": "scene type (indoor/outdoor/etc)"
}}"""

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_b64}"
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            "max_tokens": 1000,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

            try:
                # Try to parse JSON response
                clean = content.strip()
                if "```" in clean:
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                return json.loads(clean)
            except:
                return {"description": content, "objects": [], "scene": "", "text_content": ""}

    async def _groq_vision(self, image_b64: str, media_type: str, query: str) -> Dict[str, Any]:
        """Use Groq's vision-capable model"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json",
        }

        prompt = f"""Analyze this image. Describe:
1. What you see in the image
2. Main objects or subjects
3. Any visible text
4. The overall scene/setting

User's question: {query}

Be detailed and accurate."""

        payload = {
            "model": "llama-3.2-11b-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_b64}"
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            "max_tokens": 1024,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return {
                "description": content,
                "objects": self._extract_objects(content),
                "scene": self._extract_scene(content),
                "text_content": ""
            }

    def _detect_media_type(self, b64_str: str) -> str:
        """Detect image media type from base64"""
        try:
            header = base64.b64decode(b64_str[:16])
            if header[:8] == b'\x89PNG\r\n\x1a\n':
                return "image/png"
            elif header[:3] == b'\xff\xd8\xff':
                return "image/jpeg"
            elif header[:4] == b'GIF8':
                return "image/gif"
            elif header[:4] == b'RIFF':
                return "image/webp"
        except:
            pass
        return "image/jpeg"

    def _extract_objects(self, text: str) -> list:
        """Extract mentioned objects from text description"""
        common_objects = [
            "person", "car", "building", "tree", "dog", "cat", "chair",
            "table", "phone", "computer", "book", "food", "sky", "water"
        ]
        found = [obj for obj in common_objects if obj.lower() in text.lower()]
        return found[:10]

    def _extract_scene(self, text: str) -> str:
        """Extract scene type from description"""
        scenes = {
            "indoor": ["room", "office", "kitchen", "bedroom", "indoor"],
            "outdoor": ["street", "park", "outdoor", "outside", "nature"],
            "urban": ["city", "urban", "building", "road"],
            "nature": ["forest", "mountain", "beach", "sky", "grass"]
        }
        text_lower = text.lower()
        for scene, keywords in scenes.items():
            if any(kw in text_lower for kw in keywords):
                return scene
        return "general"

    def _empty_result(self) -> Dict[str, Any]:
        return {"description": "", "objects": [], "scene": "", "text_content": ""}

    def _mock_vision_result(self) -> Dict[str, Any]:
        return {
            "description": "Image received. To enable full image analysis, please configure OPENAI_API_KEY or GROQ_API_KEY with vision capabilities.",
            "objects": [],
            "scene": "unknown",
            "text_content": ""
        }


# Singleton instance
vision_service = VisionService()
