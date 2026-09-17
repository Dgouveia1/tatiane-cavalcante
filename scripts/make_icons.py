"""Gera assets/apple-touch-icon.png (180x180): fundo escuro, círculo dourado e monograma TC."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "apple-touch-icon.png"
BG, GOLD = (14, 14, 14), (201, 168, 106)


def font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("georgia.ttf", "times.ttf", "constan.ttf"):  # serifadas presentes no Windows
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def main() -> None:
    s = 4  # supersampling para bordas suaves
    size = 180 * s
    im = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(im)
    pad = 26 * s
    d.ellipse((pad, pad, size - pad, size - pad), outline=GOLD, width=3 * s)
    f = font(66 * s)
    d.text((size / 2, size / 2 - 3 * s), "TC", font=f, fill=GOLD, anchor="mm")
    im = im.resize((180, 180), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, "PNG", optimize=True)
    print(f"{OUT.name}: {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
