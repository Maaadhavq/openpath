"""Draws the app icons with Pillow: a white route mark on the OpenPath green.

    python scripts/gen_icons.py      -> app/icons/icon-192.png, icon-512.png, maskable-512.png
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

GREEN = (30, 107, 82, 255)      # --green #1e6b52
WHITE = (255, 255, 255, 255)
OUT = Path(__file__).resolve().parent.parent / "app" / "icons"


def draw(size: int, maskable: bool) -> Image.Image:
    scale = 4                                   # draw large, then downsample for smooth edges
    s = size * scale
    img = Image.new("RGBA", (s, s), GREEN if maskable else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if not maskable:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=GREEN)
    # Maskable icons keep the mark inside the central 80% safe zone.
    inner = 0.56 if maskable else 0.68
    box = s * inner
    off = (s - box) / 2
    w = box * 0.11                              # stroke width

    def pt(x: float, y: float) -> tuple[float, float]:
        return off + x * box, off + y * box

    # Route: a dot at the bottom left, an S-shaped road, a dot at the top right (the prototype's route icon).
    r = box * 0.11
    for cx, cy in ((0.14, 0.86), (0.86, 0.14)):
        x, y = pt(cx, cy)
        d.ellipse([x - r, y - r, x + r, y + r], fill=WHITE)
    def arc(x0: float, y0: float, x1: float, y1: float, start: int, end: int) -> None:
        # Pillow strokes arcs inside their box; pad by half the stroke so the arc's centre line meets the straight lines.
        a, b = pt(x0, y0)
        c, e = pt(x1, y1)
        h = w / 2
        d.arc([a - h, b - h, c + h, e + h], start=start, end=end, fill=WHITE, width=int(w))

    d.line([pt(0.26, 0.86), pt(0.62, 0.86)], fill=WHITE, width=int(w))
    arc(0.38, 0.50, 0.86, 0.86, 270, 90)
    d.line([pt(0.62, 0.50), pt(0.38, 0.50)], fill=WHITE, width=int(w))
    arc(0.14, 0.14, 0.62, 0.50, 90, 270)
    d.line([pt(0.38, 0.14), pt(0.74, 0.14)], fill=WHITE, width=int(w))
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(192, False).save(OUT / "icon-192.png")
    draw(512, False).save(OUT / "icon-512.png")
    draw(512, True).save(OUT / "maskable-512.png")
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
