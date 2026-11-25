"""Foreground window sampling (Win32) with a safe no-op fallback elsewhere."""
from __future__ import annotations

import sys

try:  # psutil is only needed to resolve process names
    import psutil
except Exception:  # pragma: no cover
    psutil = None  # type: ignore[assignment]


class LastInputInfo:  # replaced below on Windows
    cbSize = 0
    dwTime = 0


if sys.platform == "win32":  # pragma: no branch - import guard
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _user32.GetWindowTextLengthW.restype = ctypes.c_int
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetWindowTextW.restype = ctypes.c_int
    _user32.GetLastInputInfo.argtypes = [ctypes.POINTER(_LASTINPUTINFO)]
    _user32.GetLastInputInfo.restype = wintypes.BOOL
    _kernel32.GetTickCount64.restype = ctypes.c_ulonglong


def is_supported() -> bool:
    return sys.platform == "win32"


def idle_seconds() -> float:
    """Seconds since the last keyboard/mouse input (0 on unsupported platforms)."""
    if sys.platform != "win32":
        return 0.0
    info = _LASTINPUTINFO()  # type: ignore[name-defined]
    info.cbSize = ctypes.sizeof(info)  # type: ignore[name-defined]
    if not _user32.GetLastInputInfo(ctypes.byref(info)):  # type: ignore[name-defined]
        return 0.0
    ticks = _kernel32.GetTickCount64()  # type: ignore[name-defined]
    diff = int(ticks) - int(info.dwTime)
    if diff < 0:
        diff += 1 << 32
    return diff / 1000.0


def foreground() -> tuple[str, str] | None:
    """Return (process.exe, window title) of the foreground window."""
    if sys.platform != "win32":
        return None
    hwnd = _user32.GetForegroundWindow()  # type: ignore[name-defined]
    if not hwnd:
        return None
    pid = wintypes.DWORD()  # type: ignore[name-defined]
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))  # type: ignore[name-defined]
    length = _user32.GetWindowTextLengthW(hwnd)  # type: ignore[name-defined]
    buffer = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buffer, length + 1)  # type: ignore[name-defined]
    title = buffer.value
    process = ""
    if psutil is not None and pid.value:
        try:
            process = psutil.Process(pid.value).name()
        except Exception:
            process = ""
    if not process:
        process = "unknown.exe"
    return process, title
