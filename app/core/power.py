"""Power actions on the desktop: lock the workstation, send it to sleep."""
from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)


def lock_supported() -> bool:
    return sys.platform == "win32"


def lock_workstation() -> bool:
    """Lock the Windows session. Returns True when the call succeeded."""
    if sys.platform != "win32":
        log.info("lock_workstation() ignored: only Windows is supported")
        return False
    import ctypes

    try:
        result = ctypes.windll.user32.LockWorkStation()
        log.info("LockWorkStation() -> %s", result)
        return bool(result)
    except Exception:  # noqa: BLE001 - never crash the server thread
        log.exception("LockWorkStation failed")
        return False


def sleep_workstation() -> bool:
    """Suspend the computer (S3/S0 modern standby depending on policy)."""
    if sys.platform != "win32":
        return False
    import ctypes

    try:
        result = ctypes.windll.powrprof.SetSuspendState(False, True, False)
        log.info("SetSuspendState() -> %s", result)
        return bool(result)
    except Exception:  # noqa: BLE001
        log.exception("SetSuspendState failed")
        return False
