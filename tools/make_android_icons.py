"""Generate Android launcher icons (legacy + adaptive foreground) with Pillow.

    python tools/make_android_icons.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "android" / "app" / "src" / "main" / "res"

LEGACY = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
FOREGROUND = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}

TOP = (124, 108, 255)
BOTTOM = (74, 62, 214)
ACCENT = (46, 230, 168)
BASE = 1024


def gradient(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(image)
    for y in range(size):
        t = y / (size - 1)
        color = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)) + (255,)
        draw.line([(0, y), (size, y)], fill=color)
    return image


def draw_glyph(image: Image.Image, scale: float = 1.0, fill: tuple[int, int, int, int] = (255, 255, 255, 255)) -> None:
    size = image.width
    draw = ImageDraw.Draw(image)
    cx, cy = size / 2, size / 2
    body_w = size * 0.44 * scale
    body_h = size * 0.52 * scale
    left, right = cx - body_w / 2, cx + body_w / 2
    top, bottom = cy - body_h / 2, cy + body_h / 2
    stroke = max(2, int(size * 0.036 * scale))
    draw.rounded_rectangle(
        (left, top, right, bottom), radius=size * 0.05 * scale, outline=fill, width=stroke
    )
    clip_w = body_w * 0.42
    clip_h = size * 0.07 * scale
    draw.rounded_rectangle(
        (cx - clip_w / 2, top - clip_h / 2, cx + clip_w / 2, top + clip_h / 2),
        radius=clip_h / 2,
        fill=fill,
    )
    bar_w = body_w * 0.12
    gap = body_w * 0.11
    base_y = bottom - body_h * 0.16
    start_x = left + body_w * 0.18
    for idx, factor in enumerate((0.18, 0.30, 0.24)):
        height = body_h * factor
        x0 = start_x + idx * (bar_w + gap)
        color = (ACCENT + (255,)) if idx == 1 else fill
        draw.rounded_rectangle((x0, base_y - height, x0 + bar_w, base_y), radius=bar_w / 2, fill=color)


def rounded_mask(size: int, radius_ratio: float = 0.23) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * radius_ratio), fill=255)
    return mask


def circular_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    return mask


def main() -> None:
    base = gradient(BASE)
    draw_glyph(base, scale=1.0)
    base_rounded = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    base_rounded.paste(base, (0, 0), rounded_mask(BASE))

    foreground_base = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    draw_glyph(foreground_base, scale=0.62)

    for density, size in LEGACY.items():
        folder = RES / f"mipmap-{density}"
        folder.mkdir(parents=True, exist_ok=True)
        legacy = base_rounded.resize((size, size), Image.LANCZOS)
        legacy.save(folder / "ic_launcher.png")
        round_icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        round_icon.paste(base.resize((size, size), Image.LANCZOS), (0, 0), circular_mask(size))
        round_icon.save(folder / "ic_launcher_round.png")

    for density, size in FOREGROUND.items():
        folder = RES / f"mipmap-{density}"
        folder.mkdir(parents=True, exist_ok=True)
        foreground_base.resize((size, size), Image.LANCZOS).save(folder / "ic_launcher_foreground.png")

    preview = base_rounded.resize((256, 256), Image.LANCZOS)
    preview.save(ROOT / "docs" / "android-icon.png")
    print("android icons written to", RES)


if __name__ == "__main__":
    main()
