"""
Desktop service - local automation for safe command execution and file operations.
"""

import logging
import os
import re
import sys
import subprocess
import urllib.parse
import webbrowser
from typing import Any, Dict, Optional

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except Exception:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False

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
        self.safe_apps = {
            "notepad", "notepad.exe", "calc", "calc.exe", "calculator", "mspaint", "mspaint.exe",
            "explorer", "explorer.exe", "code", "code.exe", "vscode", "visual studio code",
            "chrome", "chrome.exe", "firefox", "firefox.exe", "python", "python.exe",
            "browser", "cmd", "powershell", "terminal", "spotify", "spotify.exe",
        }
        self.app_aliases = {
            "calculator": "calc",
            "browser": "chrome",
            "vscode": "code",
            "visual studio code": "code",
            "terminal": "cmd",
            "music": "spotify",
            "spotify": "spotify",
        }

    def _normalize_path(self, path: str) -> str:
        return os.path.abspath(path or "")

    def _is_safe_path(self, path: str) -> bool:
        target = self._normalize_path(path)
        return any(target == base or target.startswith(base + os.sep) for base in self.safe_dirs)

    def _is_safe_app(self, app_name: str) -> bool:
        if not app_name or not isinstance(app_name, str):
            return False
        cleaned = os.path.basename(app_name).strip().lower()
        if re.search(r"[;&|><`\\\n\r]", cleaned):
            return False
        return cleaned in self.safe_apps

    def _is_safe_mouse_keyboard(self, action: str) -> bool:
        return action in {"move", "click", "double_click", "right_click", "scroll", "type", "press", "hotkey"}

    def _is_safe_window_action(self, action: str) -> bool:
        return action in {"minimize", "maximize", "restore", "close", "activate"}

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

    async def open_application(self, app_name: str = "", path: str = "") -> Dict[str, Any]:
        """Open a desktop application by name or executable path."""
        if path:
            target = self._normalize_path(path)
            if not (self._is_safe_path(target) or self._is_safe_app(target)):
                return {"status": "error", "message": "Application path is not permitted.", "path": target}
            try:
                if self.platform.startswith("win"):
                    os.startfile(target)
                elif self.platform.startswith("darwin"):
                    subprocess.Popen(["open", target])
                else:
                    subprocess.Popen([target])
                return {"status": "ok", "action": "open_application", "path": target}
            except Exception as e:
                logger.error(f"Open application error: {e}")
                return {"status": "error", "message": str(e), "path": target}

        if app_name:
            target_name = app_name.strip().lower()
            actual = self.app_aliases.get(target_name, target_name)
            if not self._is_safe_app(actual):
                return {"status": "error", "message": "Application name is not permitted.", "app_name": app_name}
            try:
                if self.platform.startswith("win"):
                    subprocess.Popen(actual, shell=True)
                elif self.platform.startswith("darwin"):
                    subprocess.Popen(["open", actual])
                else:
                    subprocess.Popen(actual.split())
                return {"status": "ok", "action": "open_application", "app_name": actual}
            except Exception as e:
                logger.error(f"Open application error: {e}")
                return {"status": "error", "message": str(e), "app_name": app_name}

        return {"status": "error", "message": "No application name or path provided."}

    async def open_application_and_type(self, app_name: str, keys: str = "") -> Dict[str, Any]:
        """Open an application and optionally type keys into it (requires pyautogui)."""
        result = await self.open_application(app_name=app_name)
        if result.get("status") != "ok":
            return result
        # If keys provided and pyautogui is available, give the OS a moment then type
        if keys and PYAUTOGUI_AVAILABLE:
            try:
                import time
                time.sleep(0.6)
                await self.keyboard_control("type", keys)
                return {"status": "ok", "action": "open_and_type", "app_name": app_name, "keys": keys}
            except Exception as e:
                logger.error(f"Open-and-type failed: {e}")
                return {"status": "error", "message": str(e)}
        return result

    async def system_power(self, action: str) -> Dict[str, Any]:
        """Perform system power actions: shutdown, restart, lock, sleep. Requires confirmation on frontend."""
        action = (action or "").strip().lower()
        try:
            if self.platform.startswith("win"):
                if action == "shutdown":
                    subprocess.Popen(["shutdown", "/s", "/t", "0"])  # immediate
                elif action == "restart":
                    subprocess.Popen(["shutdown", "/r", "/t", "0"])  # immediate
                elif action == "sleep":
                    subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
                elif action == "lock":
                    subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
                else:
                    return {"status": "error", "message": "Unknown power action."}
            else:
                # macOS / Linux fallbacks
                if action == "shutdown":
                    subprocess.Popen(["shutdown", "-h", "now"])  # may require sudo
                elif action == "restart":
                    subprocess.Popen(["shutdown", "-r", "now"])
                elif action == "sleep":
                    subprocess.Popen(["pmset", "sleepnow"])
                elif action == "lock":
                    subprocess.Popen(["loginctl", "lock-session"])  # linux generic
                else:
                    return {"status": "error", "message": "Unknown power action."}
            return {"status": "ok", "action": "system_power", "power_action": action}
        except Exception as e:
            logger.error(f"System power error: {e}")
            return {"status": "error", "message": str(e)}

    async def find_errors_in_file(self, path: str) -> Dict[str, Any]:
        """Search a local file for lines mentioning 'error' or 'exception' and return matches."""
        target = self._normalize_path(path or "")
        if not self._is_safe_path(target):
            return {"status": "error", "message": "File access is restricted to safe local folders.", "path": target}
        try:
            matches = []
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, start=1):
                    if re.search(r"error|exception|traceback", line, re.IGNORECASE):
                        matches.append({"line": i, "text": line.strip()})
            return {"status": "ok", "path": target, "matches": matches, "total_matches": len(matches)}
        except Exception as e:
            logger.error(f"Find errors error: {e}")
            return {"status": "error", "message": str(e), "path": target}

    async def close_application(self, process_name: str) -> Dict[str, Any]:
        """Close an application by process name."""
        if not process_name or not isinstance(process_name, str):
            return {"status": "error", "message": "Process name is required."}
        cleaned = process_name.strip()
        if re.search(r"[;&|><`\\\n\r]", cleaned):
            return {"status": "error", "message": "Invalid process name."}
        try:
            if self.platform.startswith("win"):
                result = subprocess.run(["taskkill", "/IM", cleaned, "/F"], capture_output=True, text=True)
            else:
                result = subprocess.run(["pkill", "-f", cleaned], capture_output=True, text=True)
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "action": "close_application",
                "process_name": cleaned,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except Exception as e:
            logger.error(f"Close application error: {e}")
            return {"status": "error", "message": str(e), "process_name": cleaned}

    async def browser_automation(self, action: str, url: str = "") -> Dict[str, Any]:
        """Perform simple browser automation like opening or searching."""
        if not action:
            return {"status": "error", "message": "Browser action is required."}
        try:
            action = action.strip().lower()
            if action in {"open", "navigate", "open_url", "go"} and url:
                return await self.open_url(url)
            if action in {"search", "google", "find"} and url:
                query = urllib.parse.quote_plus(url)
                webbrowser.open(f"https://www.google.com/search?q={query}")
                return {"status": "ok", "action": "browser_automation", "browser_action": action, "query": url}
            return {"status": "error", "message": f"Unsupported browser action: {action}"}
        except Exception as e:
            logger.error(f"Browser automation error: {e}")
            return {"status": "error", "message": str(e)}

    async def mouse_control(
        self,
        action: str,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
    ) -> Dict[str, Any]:
        """Perform mouse control using pyautogui if available."""
        if not PYAUTOGUI_AVAILABLE:
            return {"status": "error", "message": "Mouse control requires pyautogui. Install it to enable this feature."}
        if not action or not self._is_safe_mouse_keyboard(action):
            return {"status": "error", "message": "Unsupported mouse action."}
        try:
            if action == "move":
                pyautogui.moveTo(x or pyautogui.position().x, y or pyautogui.position().y, duration=0.2)
            elif action == "click":
                pyautogui.click(x=x, y=y, clicks=clicks, button=button)
            elif action == "double_click":
                pyautogui.doubleClick(x=x, y=y, button=button)
            elif action == "right_click":
                pyautogui.click(x=x, y=y, clicks=1, button="right")
            elif action == "scroll":
                pyautogui.scroll(clicks)
            else:
                return {"status": "error", "message": "Unsupported mouse action."}
            return {"status": "ok", "action": "mouse_control", "mouse_action": action, "x": x, "y": y, "button": button, "clicks": clicks}
        except Exception as e:
            logger.error(f"Mouse control error: {e}")
            return {"status": "error", "message": str(e)}

    async def keyboard_control(self, action: str, keys: str = "") -> Dict[str, Any]:
        """Perform keyboard control using pyautogui if available."""
        if not PYAUTOGUI_AVAILABLE:
            return {"status": "error", "message": "Keyboard control requires pyautogui. Install it to enable this feature."}
        if not action or not self._is_safe_mouse_keyboard(action):
            return {"status": "error", "message": "Unsupported keyboard action."}
        try:
            if action == "type":
                pyautogui.write(keys or "", interval=0.05)
            elif action == "press":
                pyautogui.press(keys or "enter")
            elif action == "hotkey":
                pyautogui.hotkey(*[k.strip() for k in (keys or "").split("+") if k.strip()])
            else:
                return {"status": "error", "message": "Unsupported keyboard action."}
            return {"status": "ok", "action": "keyboard_control", "keyboard_action": action, "keys": keys}
        except Exception as e:
            logger.error(f"Keyboard control error: {e}")
            return {"status": "error", "message": str(e)}

    async def manage_window(self, action: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Manage windows using pyautogui if available."""
        if not PYAUTOGUI_AVAILABLE:
            return {"status": "error", "message": "Window management requires pyautogui. Install it to enable this feature."}
        if not action or not self._is_safe_window_action(action):
            return {"status": "error", "message": "Unsupported window action."}
        try:
            window = None
            if title:
                windows = pyautogui.getWindowsWithTitle(title)
                window = windows[0] if windows else None
            else:
                window = pyautogui.getActiveWindow()
            if not window:
                return {"status": "error", "message": "No matching window found."}
            if action == "minimize":
                window.minimize()
            elif action == "maximize":
                window.maximize()
            elif action == "restore":
                window.restore()
            elif action == "close":
                window.close()
            elif action == "activate":
                window.activate()
            return {"status": "ok", "action": "window_management", "window_action": action, "title": title}
        except Exception as e:
            logger.error(f"Window management error: {e}")
            return {"status": "error", "message": str(e), "window_action": action, "title": title}


# Singleton instance
desktop_service = DesktopService()
