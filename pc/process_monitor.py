"""
Process monitoring and window interception for Lockin-Inator PC.
Detects when distracting/blocked desktop applications (Claude, Antigravity, VS Code)
gain focus during a study session, without stopping their background execution.
"""
import ctypes
from ctypes import wintypes
import psutil
from typing import Optional, Tuple

user32 = ctypes.windll.user32
SW_MINIMIZE = 6


class ProcessMonitor:
    def __init__(self, blocked_processes=None):
        self.blocked_processes = [p.lower() for p in (blocked_processes or [])]
        self._pid_cache = {}

    def update_blocked_processes(self, blocked_processes):
        self.blocked_processes = [p.lower() for p in (blocked_processes or [])]
        self._pid_cache.clear()

    def get_foreground_info(self) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str]]:
        """
        Returns (hwnd, pid, process_name, window_title) of current foreground window.
        """
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None, None, None, None

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pid_val = pid.value
        if not pid_val:
            return hwnd, None, None, None

        # Check PID cache first
        pname = self._pid_cache.get(pid_val)
        if not pname:
            try:
                proc = psutil.Process(pid_val)
                pname = proc.name().lower()
                self._pid_cache[pid_val] = pname
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return hwnd, pid_val, None, None

        # Get window title
        length = user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value

        return hwnd, pid_val, pname, title

    def is_blocked(self, process_name: Optional[str]) -> bool:
        if not process_name:
            return False
        p_lower = process_name.lower()
        return any(b in p_lower for b in self.blocked_processes)

    def minimize_window(self, hwnd: int) -> bool:
        """
        Minimizes the window cleanly so background tasks continue.
        """
        if not hwnd:
            return False
        try:
            user32.ShowWindow(hwnd, SW_MINIMIZE)
            return True
        except Exception:
            return False
