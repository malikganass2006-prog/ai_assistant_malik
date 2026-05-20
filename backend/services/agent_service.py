"""
Autonomous agent service for local task planning and execution.
"""

import logging
import re
from typing import Any, Dict, List

from services.desktop_service import desktop_service
from services.llm_service import llm_service
from services.memory_service import memory_service

logger = logging.getLogger("malik.agent_service")


class AutonomousAgentService:
    """Coordinates planning, execution, and memory for autonomous tasks."""

    def __init__(self):
        self.agents = ["planner", "executor", "memory"]

    async def execute_instruction(self, instruction: str, session_id: str) -> Dict[str, Any]:
        """Create a plan from the instruction and execute desktop actions."""
        if not instruction or not instruction.strip():
            return {"status": "error", "message": "Instruction cannot be empty."}

        conversation_history = await memory_service.get_context_window(session_id)
        plan_text = await self._create_plan(instruction, conversation_history)
        actions = self._parse_actions(plan_text)
        results = []

        if not actions:
            actions = self._parse_direct_instruction(instruction)

        if not actions:
            response = await llm_service.generate_response({
                "user_input": instruction,
                "conversation_history": conversation_history,
                "intent": "agent_task",
            })
            await memory_service.add_message(session_id, "assistant", response)
            return {
                "status": "ok",
                "plan": [],
                "results": [],
                "summary": response,
            }

        for action in actions:
            result = await self._execute_action(action)
            results.append(result)

        summary = self._summarize_results(results)
        await memory_service.add_message(session_id, "assistant", summary)
        return {
            "status": "ok",
            "plan": actions,
            "results": results,
            "summary": summary,
        }

    async def _create_plan(self, instruction: str, history: List[Dict[str, str]]) -> str:
        """Ask the LLM to generate a safe desktop task plan."""
        prompt = (
            "You are a local assistant that can plan safe desktop tasks. "
            "When the user requests a desktop action, respond with a numbered action plan. "
            "Each action should be one of: run_command, list_directory, read_file, open_url, open_path. "
            "If the request is not a desktop automation task, respond with a short explanation.\n\n"
            f"User request: {instruction}\n\n"
            "Plan:" 
        )

        response = await llm_service.generate_response({
            "user_input": prompt,
            "conversation_history": history,
            "intent": "agent_planning",
        })
        return response

    def _parse_actions(self, text: str) -> List[Dict[str, Any]]:
        """Parse simple action lines from LLM output."""
        actions: List[Dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # Accept numbered plans and free-form instructions.
            line = re.sub(r'^\d+[\).]\s*', '', line)
            if ':' not in line:
                continue
            action_type, payload = map(str.strip, line.split(':', 1))
            action_type = action_type.lower().replace(' ', '_')
            action = {"type": action_type, "payload": payload}
            if action_type in ["run_command", "list_directory", "read_file", "open_url", "open_path"]:
                actions.append(action)
        return actions

    def _parse_direct_instruction(self, instruction: str) -> List[Dict[str, Any]]:
        """Parse a direct desktop instruction without LLM planning."""
        text = instruction.strip().lower()
        if not text:
            return []

        if any(keyword in text for keyword in ["run command", "execute command", "cmd ", "powershell", "bash "]):
            cmd = self._extract_quoted_text(instruction) or instruction
            return [{"type": "run_command", "payload": cmd}]

        if any(keyword in text for keyword in ["list directory", "list files", "show files", "show directory", "ls "]):
            path = self._extract_path(instruction) or "."
            return [{"type": "list_directory", "payload": path}]

        if any(keyword in text for keyword in ["read file", "open file", "view file"]):
            path = self._extract_path(instruction) or self._extract_quoted_text(instruction) or ""
            return [{"type": "read_file", "payload": path}]

        if any(keyword in text for keyword in ["open url", "visit", "go to", "open website"]):
            url = self._extract_url(instruction) or instruction
            return [{"type": "open_url", "payload": url}]

        if any(keyword in text for keyword in ["open folder", "open path", "explorer", "open directory"]):
            path = self._extract_path(instruction) or self._extract_quoted_text(instruction) or "."
            return [{"type": "open_path", "payload": path}]

        return []

    def _extract_quoted_text(self, text: str) -> str:
        match = re.search(r'"([^"]+)"|\'([^\']+)' , text)
        return match.group(1) if match else ""

    def _extract_path(self, text: str) -> str:
        match = re.search(r'(?:in|at|path|folder|directory)\s+["\']?([^"\']+)["\']?', text)
        return match.group(1).strip() if match else ""

    def _extract_url(self, text: str) -> str:
        match = re.search(r'https?://[^\s]+', text)
        if match:
            return match.group(0)
        match = re.search(r'www\.[^\s]+', text)
        return f'http://{match.group(0)}' if match else ""

    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one desktop action."""
        action_type = action.get("type")
        payload = action.get("payload", "")

        if action_type == "run_command":
            return await desktop_service.run_command(payload)
        if action_type == "list_directory":
            return await desktop_service.list_directory(payload or ".")
        if action_type == "read_file":
            return await desktop_service.read_file(payload)
        if action_type == "open_url":
            return await desktop_service.open_url(payload)
        if action_type == "open_path":
            return await desktop_service.open_path(payload)

        return {"status": "skipped", "message": f"Unsupported action type: {action_type}", "raw_payload": payload}

    def _summarize_results(self, results: List[Dict[str, Any]]) -> str:
        """Create a human-friendly summary of executed actions."""
        if not results:
            return "No desktop actions were executed."

        summaries = []
        for idx, result in enumerate(results, start=1):
            if result.get("status") == "ok":
                summaries.append(f"Step {idx}: completed {result.get('command') or result.get('action', 'task')}.")
            else:
                summaries.append(f"Step {idx}: failed - {result.get('message', 'unknown error')}")
        return "\n".join(summaries)


agent_service = AutonomousAgentService()
