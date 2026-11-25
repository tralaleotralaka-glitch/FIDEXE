"""Clipboard watcher built on top of Qt's cross-platform clipboard."""
from __future__ import annotations

import hashlib
import re

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QClipboard, QGuiApplication, QImage

from .db import Storage
from .paths import images_dir

URL_RE = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)

CODE_HINTS = (
    "def ", "class ", "function ", "const ", "let ", "var ", "import ", "from ",
    "public ", "private ", "return ", "#include", "</", "/>", "();", "=>", "console.log",
    "SELECT ", "INSERT INTO", "CREATE TABLE", "#!/",
)


def classify(text: str) -> str:
    stripped = text.strip()
    if URL_RE.match(stripped) and " " not in stripped:
        return "link"
    lowered = stripped.lower()
    code_score = sum(1 for hint in CODE_HINTS if hint.lower() in lowered)
    if code_score >= 2 or (("{" in stripped and "}" in stripped) and (";" in stripped or "\n" in stripped)) or stripped.startswith("```"):
        return "code"
    if stripped.count("\n") >= 4 and (code_score >= 1 or "  " in stripped):
        return "code"
    return "text"


class ClipboardWatcher(QObject):
    """Emits `captured` with (kind, text, image_path) for every new clipboard item."""

    captured = Signal(str, str, str)

    def __init__(self, store: Storage, *, capture_images: bool = True, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.capture_images = capture_images
        self.user_id = 0
        self._clipboard: QClipboard | None = None
        self._suspended = False
        self._last_image_hash = ""

    # ------------------------------------------------------------------ api
    def attach(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if self._clipboard is clipboard:
            return
        self._clipboard = clipboard
        clipboard.dataChanged.connect(self._on_changed)

    def suspend(self, value: bool) -> None:
        self._suspended = value

    def copy_text(self, text: str) -> None:
        if self._clipboard is None:
            self.attach()
        assert self._clipboard is not None
        self._suspended = True
        try:
            self._clipboard.setText(text)
        finally:
            self._suspended = False

    def copy_image_file(self, path: str) -> bool:
        image = QImage(path)
        if image.isNull():
            return False
        if self._clipboard is None:
            self.attach()
        assert self._clipboard is not None
        self._suspended = True
        try:
            self._clipboard.setImage(image)
        finally:
            self._suspended = False
        return True

    # -------------------------------------------------------------- internal
    def _on_changed(self) -> None:
        if self._suspended or not self.user_id or self._clipboard is None:
            return
        mime = self._clipboard.mimeData()
        if mime is None:
            return
        if mime.hasImage() and self.capture_images:
            image = self._clipboard.image()
            if image.isNull():
                return
            digest = hashlib.md5(
                f"{image.width()}x{image.height()}".encode() + bytes(image.constBits())
            ).hexdigest()
            if digest == self._last_image_hash:
                return
            self._last_image_hash = digest
            path = images_dir() / f"u{ self.user_id }-{ digest[:20] }.png"
            try:
                if image.save(str(path), "PNG"):
                    if self.store.add_clip(self.user_id, "image", "", str(path)):
                        self.captured.emit("image", "", str(path))
                    return
            except Exception:
                return
        if mime.hasText():
            text = self._clipboard.text()
            if not text or not text.strip():
                return
            if len(text) > 200_000:
                text = text[:200_000]
            kind = classify(text)
            if self.store.add_clip(self.user_id, kind, text):
                self.captured.emit(kind, text, "")
