"""Running applications: what is open right now, and closing it politely.

"Closing" means the same thing as clicking the X in the window: the app gets
WM_CLOSE and may ask to save its work. The phone cannot force-kill a process,
which keeps Windows itself out of reach.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

IS_WINDOWS = os.name == "nt"

WM_CLOSE = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# never offered for closing: Windows itself, or things that would take the
# session down with them
DENY = {
    "explorer.exe",
    "dwm.exe",
    "winlogon.exe",
    "csrss.exe",
    "services.exe",
    "lsass.exe",
    "smss.exe",
    "svchost.exe",
    "wininit.exe",
    "fontdrvhost.exe",
    "ctfmon.exe",
    "sihost.exe",
    "taskhostw.exe",
    "runtimebroker.exe",
    "system",
    "registry",
    "memory compression",
    "fidexe.exe",
}

_prototypes_ready = False


def supported() -> bool:
    return IS_WINDOWS


def _api():
    """user32/kernel32 with explicit prototypes (64-bit handles must not be truncated)."""
    global _prototypes_ready
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not _prototypes_ready:
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostMessageW.restype = wintypes.BOOL
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        _prototypes_ready = True
    return user32, kernel32


def _process_name(pid: int) -> str:
    if not IS_WINDOWS:
        return ""
    import ctypes
    from ctypes import wintypes

    try:
        _user32, kernel32 = _api()
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not handle:
            return ""
        try:
            size = wintypes.DWORD(1024)
            buffer = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return os.path.basename(buffer.value).lower()
            return ""
        finally:
            kernel32.CloseHandle(handle)
    except Exception:  # noqa: BLE001 - a single process must not break the list
        return ""


def _windows_of(pid: int | None = None) -> list[tuple[int, int, str]]:
    """Visible top-level windows: (hwnd, pid, title)."""
    if not IS_WINDOWS:
        return []
    import ctypes
    from ctypes import wintypes

    try:
        user32, _kernel32 = _api()
    except Exception:  # noqa: BLE001
        return []

    found: list[tuple[int, int, str]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            window_pid = int(owner.value)
            if window_pid <= 0:
                return True
            if pid is not None and window_pid != pid:
                return True
            found.append((int(hwnd or 0), window_pid, buffer.value))
        except Exception:  # noqa: BLE001
            pass
        return True

    try:
        user32.EnumWindows(callback, 0)
    except Exception:  # noqa: BLE001
        log.exception("Не удалось перечислить окна")
        return []
    return found


def foreground_pid() -> int:
    if not IS_WINDOWS:
        return 0
    import ctypes
    from ctypes import wintypes

    try:
        user32, _kernel32 = _api()
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return 0
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        return int(owner.value)
    except Exception:  # noqa: BLE001
        return 0


def list_apps(limit: int = 24) -> list[dict]:
    """Visible applications with a window; the foreground one comes first."""
    if not IS_WINDOWS:
        return []
    active = foreground_pid()
    apps: dict[int, dict] = {}
    for _hwnd, window_pid, title in _windows_of():
        if window_pid == os.getpid():
            continue
        name = _process_name(window_pid)
        if not name or name in DENY:
            continue
        entry = apps.get(window_pid)
        if entry is None:
            apps[window_pid] = {
                "pid": window_pid,
                "app": name,
                "title": title,
                "active": window_pid == active,
            }
        elif window_pid == active:
            entry.update({"title": title, "active": True})
    ordered = sorted(apps.values(), key=lambda item: (not item["active"], item["app"]))
    return ordered[:limit]


def close_app(pid: int) -> bool:
    """Ask every window of the process to close (WM_CLOSE), like clicking X."""
    if not IS_WINDOWS:
        return False
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    name = _process_name(pid)
    if name in DENY:
        log.warning("Отказ закрывать системный процесс %s (%s)", name, pid)
        return False
    try:
        user32, _kernel32 = _api()
    except Exception:  # noqa: BLE001
        return False
    sent = 0
    for hwnd, _window_pid, _title in _windows_of(pid):
        if user32.PostMessageW(hwnd, WM_CLOSE, 0, 0):
            sent += 1
    log.info("Закрываю %s (pid %s): отправлено %s WM_CLOSE", name or "?", pid, sent)
    return sent > 0
