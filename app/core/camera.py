"""Webcam snapshots for the Android app.

The phone never touches the camera directly: it asks the desktop for a JPEG
several times per second and shows the frames as pictures. The camera is opened
lazily on the first request and released again after a few idle seconds, so the
LED is not on when nobody is watching.
"""
from __future__ import annotations

import logging
import threading
import time

try:  # bundled into the exe by PyInstaller; optional for source runs
    import cv2  # type: ignore
except Exception:  # noqa: BLE001 - the app must start without opencv
    cv2 = None

log = logging.getLogger(__name__)

CAMERA_IDLE_STOP = 25.0     # release the device when the phone stops asking
CAMERA_FPS = 8
JPEG_QUALITY = 70
FRAME_WAIT = 4.0


class CameraUnavailable(Exception):
    """Camera cannot deliver a frame; the message is shown on the phone."""


class CameraService:
    """Threaded grabber that keeps only the latest JPEG frame in memory."""

    def __init__(self, index: int = 0) -> None:
        self.index = index
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._frame: bytes | None = None
        self._size: tuple[int, int] = (0, 0)
        self._last_request = 0.0
        self._error = ""

    # ------------------------------------------------------------------ info
    @property
    def supported(self) -> bool:
        return cv2 is not None

    def info(self) -> dict:
        thread = self._thread
        with self._lock:
            size = self._size
            error = self._error
        return {
            "supported": self.supported,
            "active": bool(thread is not None and thread.is_alive()),
            "width": size[0],
            "height": size[1],
            "fps": CAMERA_FPS,
            "error": error,
        }

    # -------------------------------------------------------------- grabbing
    def _ensure_running(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._error = ""
            self._frame = None
            self._thread = threading.Thread(target=self._loop, name="fidexe-camera", daemon=True)
            self._thread.start()

    def _loop(self) -> None:
        capture = None
        try:
            backend = getattr(cv2, "CAP_DSHOW", 0)
            capture = cv2.VideoCapture(self.index, backend) if backend else cv2.VideoCapture(self.index)
            if not capture.isOpened():
                with self._lock:
                    self._error = "камера не найдена или занята другой программой"
                return
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
            pause = 1.0 / CAMERA_FPS
            while not self._stop.is_set():
                if time.time() - self._last_request > CAMERA_IDLE_STOP:
                    break
                ok, frame = capture.read()
                if not ok:
                    with self._lock:
                        self._error = "кадр не получен — камера занята?"
                    time.sleep(0.3)
                    continue
                encoded, buffer = cv2.imencode(
                    ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                )
                if encoded:
                    with self._lock:
                        self._frame = buffer.tobytes()
                        self._size = (int(frame.shape[1]), int(frame.shape[0]))
                        self._error = ""
                time.sleep(pause)
        except Exception as exc:  # noqa: BLE001 - never kill the server thread
            log.exception("Ошибка работы с камерой")
            with self._lock:
                self._error = f"ошибка камеры: {exc}"
        finally:
            if capture is not None:
                try:
                    capture.release()
                except Exception:  # noqa: BLE001
                    pass
            with self._lock:
                self._thread = None
                self._frame = None
            log.info("Камера закрыта")

    def snapshot(self, wait: float = FRAME_WAIT) -> bytes:
        """Return one JPEG frame, opening the camera if needed."""
        if cv2 is None:
            raise CameraUnavailable(
                "на ноутбуке недоступна камера: модуль opencv не установлен (используйте сборку с exe)"
            )
        self._last_request = time.time()
        self._ensure_running()
        deadline = time.time() + wait
        while time.time() < deadline:
            with self._lock:
                frame = self._frame
                error = self._error
                alive = self._thread is not None and self._thread.is_alive()
            if frame:
                return frame
            if error and not alive:
                raise CameraUnavailable(error)
            time.sleep(0.05)
        raise CameraUnavailable(self._error or "камера не отвечает")

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
