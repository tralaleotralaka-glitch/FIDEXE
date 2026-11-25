"""Inline SVG icon set rendered to QIcon/QPixmap on the fly."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_SVG: dict[str, str] = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    "clipboard": '<rect x="8" y="2.5" width="8" height="4" rx="1.5"/><path d="M16 4.5h2a2 2 0 0 1 2 2V20a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2h2"/><path d="M8 12h8M8 16h5"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-6M22 20H2"/>',
    "settings": '<circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.6 1.6 0 0 0 .32 1.77l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.6 1.6 0 0 0-1.77-.32 1.6 1.6 0 0 0-1 1.47V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1.05-1.47 1.6 1.6 0 0 0-1.77.32l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.6 1.6 0 0 0 .32-1.77 1.6 1.6 0 0 0-1.47-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.47-1.05 1.6 1.6 0 0 0-.32-1.77l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.6 1.6 0 0 0 1.77.32H9a1.6 1.6 0 0 0 1-1.47V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.47 1.6 1.6 0 0 0 1.77-.32l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.6 1.6 0 0 0-.32 1.77V9a1.6 1.6 0 0 0 1.47 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1Z"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "trash": '<path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13"/><path d="M10 11v6M14 11v6"/>',
    "pin": '<path d="M9 3h6l-1 6 3.5 3.5H6.5L10 9 9 3Z"/><path d="M12 12.5V21"/>',
    "copy": '<rect x="9" y="9" width="12" height="12" rx="2.5"/><path d="M15 5.5A2.5 2.5 0 0 0 12.5 3H5.5A2.5 2.5 0 0 0 3 5.5v7A2.5 2.5 0 0 0 5.5 15"/>',
    "export": '<path d="M12 3v12"/><path d="m7.5 10.5 4.5 4.5 4.5-4.5"/><path d="M4 17v2.5A1.5 1.5 0 0 0 5.5 21h13a1.5 1.5 0 0 0 1.5-1.5V17"/>',
    "power": '<path d="M12 3v9"/><path d="M6.4 6.4a8 8 0 1 0 11.2 0"/>',
    "check": '<path d="m4 12.5 5 5L20 6.5"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="9" cy="9.5" r="1.8"/><path d="m4 18 5-5 4 4 3-3 4 4"/>',
    "link": '<path d="M10 13.5a4.5 4.5 0 0 0 6.4 0l2.1-2.1a4.5 4.5 0 1 0-6.4-6.4L11 6"/><path d="M14 10.5a4.5 4.5 0 0 0-6.4 0l-2.1 2.1a4.5 4.5 0 1 0 6.4 6.4L13 18"/>',
    "text": '<path d="M5 6V4.5h14V6"/><path d="M12 4.5V20"/><path d="M9 20h6"/>',
    "code": '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M13.5 4l-3 16"/>',
    "play": '<path d="M7 4.5 19 12 7 19.5Z"/>',
    "pause": '<rect x="7" y="4.5" width="3.5" height="15" rx="1.2"/><rect x="13.5" y="4.5" width="3.5" height="15" rx="1.2"/>',
    "mail": '<rect x="2.5" y="4.5" width="19" height="15" rx="2.5"/><path d="m3 7 8.2 5.6a1.5 1.5 0 0 0 1.6 0L21 7"/>',
    "lock": '<rect x="4.5" y="10" width="15" height="10.5" rx="2.5"/><path d="M8 10V7.5a4 4 0 0 1 8 0V10"/>',
    "eye": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
    "eye-off": '<path d="M4 4l16 16"/><path d="M9.9 5.9A9.6 9.6 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.8 3.6"/><path d="M6.2 8.3A16.9 16.9 0 0 0 2.5 12S6 18.5 12 18.5c1.2 0 2.3-.25 3.3-.65"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5V12l3.2 2"/>',
    "apps": '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
    "flame": '<path d="M12 2.5s6 5 6 10.5a6 6 0 0 1-12 0c0-2 1-3.5 2-4.5 0 2 1 3 2.5 3.5C11 9 11.5 5.5 12 2.5Z"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2.5"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "shield": '<path d="M12 2.8 20 6v6c0 5-3.4 8-8 9.2C7.4 20 4 17 4 12V6l8-3.2Z"/><path d="m8.8 12 2.2 2.2 4.2-4.2"/>',
    "sparkle": '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3Z"/><path d="M18.5 15.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8.8-2Z"/>',
    "logout": '<path d="M15 4h3.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H15"/><path d="M10 8l-4 4 4 4M6 12h9"/>',
    "chevron-down": '<path d="m6 9.5 6 6 6-6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "filter": '<path d="M3 5h18l-7 8v6l-4 2v-8L3 5Z"/>',
    "arrow-up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "arrow-down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "download": '<path d="M12 3v12"/><path d="m7.5 10.5 4.5 4.5 4.5-4.5"/><path d="M4 17v2.5A1.5 1.5 0 0 0 5.5 21h13a1.5 1.5 0 0 0 1.5-1.5V17"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.6v.2"/>',
    "monitor": '<rect x="2.5" y="4" width="19" height="13" rx="2.5"/><path d="M9 21h6M12 17v4"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.6-5.9"/><path d="M20 3.5V9h-5.4"/>',
    "key": '<circle cx="8" cy="12" r="4"/><path d="M12 12h9M17.5 12v3M20 12v2"/>',
}


def pixmap(name: str, color: str = "#ECEEF7", size: int = 20, dpr: float = 2.0) -> QPixmap:
    body = _SVG.get(name, _SVG["info"])
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pm


def icon(name: str, color: str = "#ECEEF7", size: int = 20) -> QIcon:
    return QIcon(pixmap(name, color, size))


def app_icon_text(name: str) -> str:
    return name
