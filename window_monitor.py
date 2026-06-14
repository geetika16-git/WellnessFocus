import sys
import platform
import time
from datetime import datetime
from database import DatabaseManager

if platform.system() == "Windows":
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    GetForegroundWindow = user32.GetForegroundWindow
    GetWindowTextW = user32.GetWindowTextW
    GetWindowTextLengthW = user32.GetWindowTextLengthW
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId

    OpenProcess = kernel32.OpenProcess
    CloseHandle = kernel32.CloseHandle
    GetModuleBaseNameW = kernel32.GetModuleBaseNameW

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

class WindowMonitor:
    def __init__(self, user_id, poll_interval=1):
        self.user_id = user_id
        self.poll_interval = poll_interval
        self.last_process = None
        self.last_title = None
        self.session_start = None
        self.running = False

    def start(self):
        self.running = True
        if platform.system() == "Windows":
            self._poll_loop_windows()
        else:
            self._poll_loop_stub()

    def stop(self):
        self.running = False

    def _get_active_window_info_windows(self):
        try:
            hwnd = GetForegroundWindow()
            if not hwnd:
                return None, None

            length = GetWindowTextLengthW(hwnd) + 1
            buffer = ctypes.create_unicode_buffer(length)
            GetWindowTextW(hwnd, buffer, length)
            title = buffer.value

            pid = ctypes.wintypes.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            process_handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value)
            if not process_handle:
                return None, title

            exe_buffer = ctypes.create_unicode_buffer(260)
            GetModuleBaseNameW(process_handle, None, exe_buffer, 260)
            process_name = exe_buffer.value
            CloseHandle(process_handle)

            return process_name, title
        except Exception:
            return None, None

    def _poll_loop_windows(self):
        while self.running:
            process, title = self._get_active_window_info_windows()

            if process and process != self.last_process:
                if self.last_process and self.session_start:
                    elapsed = time.time() - self.session_start
                    if elapsed >= 1:
                        DatabaseManager.log_app_usage(
                            self.user_id,
                            self.last_process,
                            self.last_title,
                            int(elapsed)
                        )

                self.last_process = process
                self.last_title = title
                self.session_start = time.time()

            elif process == self.last_process and title != self.last_title:
                self.last_title = title

            time.sleep(self.poll_interval)

        if self.last_process and self.session_start:
            elapsed = time.time() - self.session_start
            if elapsed >= 1:
                DatabaseManager.log_app_usage(
                    self.user_id,
                    self.last_process,
                    self.last_title,
                    int(elapsed)
                )

    def _poll_loop_stub(self):
        while self.running:
            time.sleep(1)

    def get_current_process(self):
        if platform.system() == "Windows":
            process, title = self._get_active_window_info_windows()
            return process or "unknown", title or ""
        return "unknown", ""
