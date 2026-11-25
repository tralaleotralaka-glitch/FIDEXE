"""Generate the application icon (PNG + multi-size ICO) with Pillow.

Run:  python tools/make_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "app" / "assets"
SIZE = 1024

TOP = (124, 108, 255)
BOTTOM = (74, 62, 214)
ACCENT = (46, 230, 168)


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def build() -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    gradient = Image.new("RGBA", (SIZE, SIZE))
    draw = ImageDraw.Draw(gradient)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        color = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)) + (255,)
        draw.line([(0, y), (SIZE, y)], fill=color)

    # soft highlight in the top-left corner
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((-SIZE * 0.25, -SIZE * 0.35, SIZE * 0.75, SIZE * 0.55), fill=(255, 255, 255, 42))
    gradient = Image.alpha_composite(gradient, glow)

    image.paste(gradient, (0, 0), rounded_mask(SIZE, int(SIZE * 0.23)))
    draw = ImageDraw.Draw(image)

    # clipboard body
    left, right = SIZE * 0.26, SIZE * 0.74
    top, bottom = SIZE * 0.24, SIZE * 0.80
    radius = SIZE * 0.06
    width = int(SIZE * 0.045)
    draw.rounded_rectangle((left, top, right, bottom), radius=radius, outline=(255, 255, 255, 255), width=width)

    # clip at the top
    clip_w = (right - left) * 0.42
    clip_h = SIZE * 0.085
    cx = (left + right) / 2
    draw.rounded_rectangle(
        (cx - clip_w / 2, top - clip_h / 2, cx + clip_w / 2, top + clip_h / 2),
        radius=clip_h / 2,
        fill=(255, 255, 255, 255),
        outline=(255, 255, 255, 255),
    )

    # bars inside
    bar_bottom = bottom - (bottom - top) * 0.17
    bar_width = (right - left) * 0.115
    gap = (right - left) * 0.11
    start_x = left + (right - left) * 0.20
    heights = (0.20, 0.34, 0.27)
    for idx, factor in enumerate(heights):
        h = (bottom - top) * factor
        x0 = start_x + idx * (bar_width + gap)
        color = ACCENT + (255,) if idx == 1 else (255, 255, 255, 235)
        draw.rounded_rectangle((x0, bar_bottom - h, x0 + bar_width, bar_bottom), radius=bar_width / 2, fill=color)

    return image


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = build()
    icon.resize((512, 512), Image.LANCZOS).save(ASSETS / "app.png")
    icon.resize((256, 256), Image.LANCZOS).save(ASSETS / "app_256.png")
    icon.save(
        ASSETS / "app.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("wrote", ASSETS / "app.ico")


if __name__ == "__main__":
    main()
