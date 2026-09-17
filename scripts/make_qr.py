"""
Gera assets/qr.svg apontando para a URL do cartão.

Uso:
    python scripts/make_qr.py https://dominio-final.com.br/

Correção de erro "H" (30%) porque o HTML sobrepõe o selo "TC" no centro do QR.
Regenerar quando o domínio final for definido (ver README).
"""
import sys
from pathlib import Path

import segno

DEFAULT_URL = "http://tatianecavalcantieug1780939127959.0630367.meusitehostgator.com.br/"  # URL temporária da HostGator
OUT = Path(__file__).resolve().parent.parent / "assets" / "qr.svg"


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    qr = segno.make(url, error="h")
    qr.save(str(OUT), kind="svg", scale=6, border=1, dark="#0e0e0e", light=None, xmldecl=False, svgns=True, omitsize=True)
    print(f"{OUT.name}: {url} (versão {qr.version}, {OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
