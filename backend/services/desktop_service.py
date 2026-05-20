"""
Desktop service - local automation for safe command execution and file operations.
"""

import logging
import os
import re
import sys
import subprocess
import webbrowser
from typing import Any, Dict, Optional

logger = logging.getLogger("malik.desktop_service")


class DesktopService:
    """Provides local desktop automation and system control."""

    def __init__(self):
        self.platform = sys.platform
        self.safe_dirs = [
            os.path.abspath(os.getcwd()),
            os.path.expanduser("~"),
        ]
        self.safe_commands = {
            "dir",
            "ls",
            "echo",
            "type",
            "cat",
            "pwd",
            "whoami",
            "hostname",
            "ver",
            "date",
            "time",
        }

    def _normalize_path(self, path: str) -> str:
        return os.path.abspath(path or "")

    def _is_safe_path(self, path: str) -> bool:
        target = self._normalize_path(path)
        return any(target == base or target.startswith(base + os.sep) for base in self.safe_dirs)

    def _is_safe_command(self, command: str) -> bool:
        if not command or not isinstance(command, str):
            return False
        cleaned = command.strip()
        if not cleaned:
            return False
        if re.search(r'[;&|><`\\\n\r]', cleaned):
            return False
        parts = cleaned.split()
        if not parts:
            return False
        verb = parts[0].lower()
        return verb in self.safe_commands

    async def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a shell command and return stdout/stderr."""
        if not command or not isinstance(command, str):
            return {"status": "error", "message": "Command must be a non-empty string."}
        if not self._is_safe_command(command):
            return {"status": "error", "message": "Command is not permitted. Only limited safe desktop commands are allowed."}

        try:
            logger.info(f"Running desktop command: {command}")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "status": "ok",
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Command timeout: {command}")
            return {"status": "timeout", "message": str(e)}
        except Exception as e:
            logger.error(f"Desktop command error: {e}")
            return {"status": "error", "message": str(e)}

    async def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """List files and folders in a directory."""
        target = self._normalize_path(path or ".")
        if not self._is_safe_path(target):
            return {"status": "error", "message": "Directory access is restricted to safe local folders.", "path": target}
        try:
            items = os.listdir(target)
            return {"status": "ok", "path": target, "items": sorted(items)}
        except Exception as e:
            logger.error(f"List directory error: {e}")
            return {"status": "error", "message": str(e), "path": target}

    async def read_file(self, path: str, max_bytes: int = 16384) -> Dict[str, Any]:
        """Read a file from disk with a byte limit."""
        target = self._normalize_path(path or "")
        if not self._is_safe_path(target):
            return {"status": "error", "message": "File access is restricted to safe local folders.", "path": target}
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)
            return {"status": "ok", "path": target, "content": content}
        except Exception as e:
            logger.error(f"Read file error: {e}")
            return {"status": "error", "message": str(e), "path": target}

    async def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in the default browser."""
        try:
            if not url or not isinstance(url, str):
                raise ValueError("URL must be a non-empty string.")
            normalized = url.strip()
            if not normalized.startswith("http://") and not normalized.startswith("https://"):
                normalized = "https://" + normalized
            webbrowser.open(normalized)
            return {"status": "ok", "action": "open_url", "url": normalized}
        except Exception as e:
            logger.error(f"Open URL error: {e}")
            return {"status": "error", "message": str(e)}

    async def open_path(self, path: str) -> Dict[str, Any]:
        """Open a file or folder using the OS default application."""
        target = self._normalize_path(path or "")
        if not self._is_safe_path(target):
            return {"status": "error", "message": "Path opening is restricted to safe local folders.", "path": target}
        try:
            if self.platform.startswith("win"):
                os.startfile(target)
            elif self.platform.startswith("darwin"):
                subprocess.run(["open", target], check=True)
            else:
                subprocess.run(["xdg-open", target], check=True)
            return {"status": "ok", "action": "open_path", "path": target}
        except Exception as e:
            logger.error(f"Open path error: {e}")
            return {"status": "error", "message": str(e), "path": target}


# Singleton instance
desktop_service = DesktopService()
