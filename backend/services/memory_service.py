"""
Memory Service - Manages conversation history and context
Supports short-term (session) and long-term (file) memory
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import asyncio

from config import settings

logger = logging.getLogger("malik.memory_service")


class MemoryService:
    """Manages conversation memory across sessions"""

    def __init__(self):
        self.short_term: Dict[str, List[Dict]] = defaultdict(list)
        self.memory_file = settings.MEMORY_FILE_PATH
        self.max_history = settings.MEMORY_MAX_HISTORY
        self._lock = asyncio.Lock()

        # Load persisted memory if file-based
        if settings.MEMORY_TYPE == "file":
            self._load_from_file()

    def _load_from_file(self):
        """Load conversation history from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for session_id, history in data.items():
                        self.short_term[session_id] = history
                logger.info(f"Loaded {len(self.short_term)} sessions from memory file")
        except Exception as e:
            logger.error(f"Failed to load memory file: {e}")

    async def _save_to_file(self):
        """Persist conversation history to file"""
        if settings.MEMORY_TYPE != "file":
            return
        try:
            async with self._lock:
                with open(self.memory_file, "w", encoding="utf-8") as f:
                    json.dump(dict(self.short_term), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    async def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            message.update(metadata)

        self.short_term[session_id].append(message)

        # Trim history if too long
        if len(self.short_term[session_id]) > self.max_history:
            self.short_term[session_id] = self.short_term[session_id][-self.max_history:]

        await self._save_to_file()
        logger.debug(f"Added {role} message to session {session_id[:8]}...")

    async def get_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        return self.short_term.get(session_id, [])

    async def clear_session(self, session_id: str):
        """Clear history for a session"""
        if session_id in self.short_term:
            del self.short_term[session_id]
            await self._save_to_file()
            logger.info(f"Cleared session {session_id[:8]}...")

    async def get_context_window(self, session_id: str, max_messages: int = 20) -> List[Dict]:
        """Get recent conversation context for LLM"""
        history = await self.get_history(session_id)
        # Return only role + content for LLM context
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history[-max_messages:]
        ]

    async def export_session(self, session_id: str) -> Dict[str, Any]:
        """Export full session data"""
        history = await self.get_history(session_id)
        return {
            "session_id": session_id,
            "exported_at": datetime.utcnow().isoformat(),
            "total_messages": len(history),
            "history": history,
        }

    def get_all_sessions(self) -> List[str]:
        """Get all active session IDs"""
        return list(self.short_term.keys())


# Singleton instance
memory_service = MemoryService()
