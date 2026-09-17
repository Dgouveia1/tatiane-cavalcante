"""
Baixa as fontes do Google Fonts (subset latin, woff2) para assets/fonts/ e gera css/fonts.css.

Uso:  python scripts/fetch_fonts.py

Por que self-host: o <link> do Google Fonts é uma requisição externa bloqueante de renderização
(DNS + TLS + CSS + woff2). Servindo do próprio domínio, com preload, o texto aparece antes.
"""
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "assets" / "fonts"
OUT_CSS = ROOT / "css" / "fonts.css"

# Inter é variável: pedir o intervalo 400..600 devolve UM arquivo com font-weight "400 600"
FAMILIES = "family=Cormorant+Garamond:wght@600&family=Inter:wght@400..600&family=Great+Vibes&display=swap"
CSS_URL = f"https://fonts.googleapis.com/css2?{FAMILIES}"
# UA moderno => o Google devolve woff2 com unicode-range por subset
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")

FACE_RE = re.compile(r"/\*\s*(?P<subset>[\w-]+)\s*\*/\s*@font-face\s*\{(?P<body>.*?)\}", re.S)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def prop(body: str, name: str) -> str:
    m = re.search(rf"{name}\s*:\s*([^;]+);", body)
    return m.group(1).strip() if m else ""


def main() -> None:
    css = fetch(CSS_URL).decode("utf-8")
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    rules = []
    for m in FACE_RE.finditer(css):
        if m.group("subset") != "latin":  # português cabe no latin (Latin-1: ã ç é õ ...)
            continue
        body = m.group("body")
        family = prop(body, "font-family").strip("'\"")
        weight = prop(body, "font-weight")
        style = prop(body, "font-style")
        url = re.search(r"url\((https://[^)]+\.woff2)\)", body).group(1)
        unicode_range = prop(body, "unicode-range")

        slug = family.lower().replace(" ", "-")
        fname = f"{slug}-{weight.replace(' ', '-')}{'-italic' if style == 'italic' else ''}.woff2"
        (FONTS_DIR / fname).write_bytes(fetch(url))
        rules.append(
            "@font-face {\n"
            f"  font-family: \"{family}\";\n"
            f"  font-style: {style};\n"
            f"  font-weight: {weight};\n"
            "  font-display: swap;\n"
            f"  src: url(\"../assets/fonts/{fname}\") format(\"woff2\");\n"
            f"  unicode-range: {unicode_range};\n"
            "}"
        )
        print(f"{fname}: {(FONTS_DIR / fname).stat().st_size // 1024} KB")

    header = ("/* Fontes self-hosted (Google Fonts, subset latin). Gerado por scripts/fetch_fonts.py — não editar à mão.\n"
              "   Licenças: Cormorant Garamond (OFL), Inter (OFL), Great Vibes (OFL). */\n\n")
    OUT_CSS.write_text(header + "\n\n".join(rules) + "\n", encoding="utf-8", newline="\n")
    print(f"{OUT_CSS.relative_to(ROOT)}: {len(rules)} @font-face")


if __name__ == "__main__":
    main()
