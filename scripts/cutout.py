"""
Recorta o fundo da foto e gera assets/tati.webp + assets/tati.png.

Uso:
    python scripts/cutout.py                # rembg -> isnet em WASM (Node) -> GrabCut (OpenCV), o primeiro que funcionar
    python scripts/cutout.py --grabcut      # força GrabCut
    python scripts/cutout.py --preview      # também salva scripts/_raw/preview.png (fundo escuro)

Entrada: scripts/_raw/tati.jpg (foto original, git-ignored).
Requisitos: pip install opencv-python-headless pillow
Opcional (bordas muito melhores): rembg ("pip install rembg[cpu]", exige VC++ Redistributable no Windows)
  ou Node + "npm i onnxruntime-web" + modelo em scripts/_raw/isnet-general-use.onnx (ver ISNET_URL).

O GrabCut foi calibrado para ESTA foto (parede cinza-clara, sombra quente à direita, calça verde-sálvia, piso de madeira).
Se a cliente mandar outra foto, prefira o rembg ou ajuste as constantes abaixo.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "scripts" / "_raw" / "tati.jpg"
OUT_WEBP = ROOT / "assets" / "tati.webp"
OUT_PNG = ROOT / "assets" / "tati.png"
PREVIEW = ROOT / "scripts" / "_raw" / "preview.png"

CROP_Y1 = None         # None = corpo inteiro (cabeça aos sapatos). Use 520 para cortar acima do rodapé/chão (até o joelho)
RECT = (395, 15, 770)  # x0, y0, x1 do retângulo "provavelmente frente" (y1 = CROP_Y1)
OUT_HEIGHT = 960       # altura final em px (largura segue a proporção); exibida a no máx. ~250 css px de largura => 2x DPR

# modelo do rembg, para o caminho WASM (git-ignored; ~176 MB)
ISNET_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"
ISNET_MODEL = ROOT / "scripts" / "_raw" / "isnet-general-use.onnx"


def cut_rembg(bgr: np.ndarray) -> np.ndarray:
    from rembg import new_session, remove  # noqa: WPS433 (import opcional)

    session = new_session("isnet-general-use")
    rgba = remove(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), session=session)
    return np.asarray(rgba)[:, :, 3]


def cut_isnet_wasm(bgr: np.ndarray) -> np.ndarray:
    """Mesmo modelo do rembg (isnet-general-use), rodado em WASM pelo Node (scripts/isnet_wasm.js).

    Pré/pós-processamento copiados do rembg (DisSession): resize 1024², mean .5 / std 1, min-max no output.
    """
    import shutil
    import subprocess
    import tempfile

    model = ISNET_MODEL
    if not model.exists():
        raise FileNotFoundError(f"modelo não encontrado: {model} (baixe de {ISNET_URL})")
    node = shutil.which("node")
    if not node:
        raise FileNotFoundError("node não encontrado no PATH")

    size = 1024
    rgb = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).resize((size, size), Image.LANCZOS)
    arr = np.asarray(rgb).astype(np.float32)
    arr = arr / max(arr.max(), 1e-6)
    arr = (arr - 0.5) / 1.0
    tensor = np.ascontiguousarray(arr.transpose(2, 0, 1)[None], dtype=np.float32)  # 1x3xSxS

    with tempfile.TemporaryDirectory() as tmp:
        fin = Path(tmp) / "in.f32"
        fout = Path(tmp) / "out.f32"
        tensor.tofile(fin)
        subprocess.run([node, str(ROOT / "scripts" / "isnet_wasm.js"), str(model), str(fin), str(fout), str(size)],
                       check=True)
        pred = np.fromfile(fout, dtype=np.float32)

    pred = pred[: size * size].reshape(size, size)
    pred = (pred - pred.min()) / max(pred.max() - pred.min(), 1e-6)
    mask = Image.fromarray((pred * 255).astype(np.uint8), "L").resize((bgr.shape[1], bgr.shape[0]), Image.LANCZOS)
    return np.asarray(mask)


def refine_with_grabcut(bgr: np.ndarray, soft: np.ndarray) -> np.ndarray:
    """Usa o alpha (0-255) de um modelo de matting como prior do GrabCut e devolve o alpha refinado.

    O modelo acerta silhueta/cabelo mas deixa um halo semitransparente onde o fundo tem pouco
    contraste (parede sombreada x calça clara). O GrabCut modela as cores e decide o halo;
    dentro do que ele confirma como frente, mantemos as bordas macias do modelo.
    """
    a = soft.astype(np.float32) / 255.0
    work = cv2.bilateralFilter(bgr, 7, 40, 40)

    mask = np.full(a.shape, cv2.GC_PR_BGD, np.uint8)
    mask[a > 0.5] = cv2.GC_PR_FGD
    mask[a >= 0.97] = cv2.GC_FGD
    mask[a <= 0.03] = cv2.GC_BGD
    sure = cv2.erode((mask == cv2.GC_FGD).astype(np.uint8), np.ones((5, 5), np.uint8))
    mask[(mask == cv2.GC_FGD) & (sure == 0)] = cv2.GC_PR_FGD  # "certamente frente" não encosta na borda

    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(work, mask, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    hard = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.uint8)
    hard = cv2.morphologyEx(_largest_component(hard), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    band = cv2.dilate(hard, np.ones((3, 3), np.uint8)).astype(np.float32)
    stretched = np.clip((a - 0.25) / (0.80 - 0.25), 0, 1)          # calça (0.83+) vira opaca, halo (<0.6) some
    alpha = stretched * band
    inside = np.clip((a - 0.10) / 0.50, 0, 1)                       # dentro da máscara, mínimo mais generoso
    alpha = np.where(hard == 1, np.maximum(alpha, inside), alpha)
    return (alpha * 255).astype(np.uint8)


def cut_grabcut(bgr: np.ndarray) -> np.ndarray:
    work = cv2.bilateralFilter(bgr, 7, 40, 40)  # suaviza artefatos JPEG sem borrar bordas
    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    wall = (sat < 40) & (val > 150)  # parede (inclui a sombra, que é neutra)

    mask = np.full(work.shape[:2], cv2.GC_PR_BGD, np.uint8)
    x0, y0, x1 = RECT
    mask[y0:, x0:x1] = cv2.GC_PR_FGD
    # piso de madeira (quente e saturado) também é fundo
    floor = (hue < 30) & (sat > 80) & (val > 110)
    floor[:540, :] = False
    wall = wall | floor

    # parede "certamente fundo": pixels de parede a mais de 6px de qualquer pixel não-parede
    dist_to_notwall = cv2.distanceTransform(wall.astype(np.uint8), cv2.DIST_L2, 3)
    mask[wall & (dist_to_notwall > 6)] = cv2.GC_BGD

    # núcleos "certamente frente": escuros (cabelo/blazer/notebook) e a calça (verde saturado)
    dark = cv2.erode((val < 90).astype(np.uint8), np.ones((9, 9), np.uint8))
    pants = cv2.erode(((sat > 55) & (val > 100) & (val < 200)).astype(np.uint8), np.ones((11, 11), np.uint8))
    mask[((dark == 1) | (pants == 1)) & (mask == cv2.GC_PR_FGD)] = cv2.GC_FGD

    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(work, mask, None, bgd, fgd, 8, cv2.GC_INIT_WITH_MASK)
    hard = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.uint8)

    # remove faixas de parede coladas ao corpo: pixels cor-de-parede a até 30px do fundo
    # (a borda da imagem conta como fundo, por isso o pad)
    wallish = ((sat < 40) & (val > 150)) | ((sat < 54) & (hue < 20) & (val > 150))
    for _ in range(4):
        padded = np.pad(hard, 1)
        dist_to_bg = cv2.distanceTransform(padded, cv2.DIST_L2, 3)[1:-1, 1:-1]
        hard[wallish & (dist_to_bg < 30)] = 0

    hard = _largest_component(hard)
    hard = cv2.morphologyEx(hard, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    hard = cv2.morphologyEx(hard, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    hard = _largest_component(hard)
    return cv2.GaussianBlur(hard * 255, (3, 3), 0)


def _largest_component(binary: np.ndarray) -> np.ndarray:
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    if n <= 1:
        return binary
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (labels == biggest).astype(np.uint8)


def main() -> None:
    force_grabcut = "--grabcut" in sys.argv
    want_preview = "--preview" in sys.argv

    if not RAW.exists():
        sys.exit(f"Foto original não encontrada: {RAW}")

    bgr = cv2.imread(str(RAW))
    if CROP_Y1:
        bgr = bgr[:CROP_Y1]

    alpha = None
    if not force_grabcut:
        attempts = (("rembg (isnet-general-use)", cut_rembg), ("isnet-general-use via WASM/Node", cut_isnet_wasm))
        for label, fn in attempts:
            try:
                alpha = refine_with_grabcut(bgr, fn(bgr))
                print(f"recorte: {label} + refino GrabCut")
                break
            except (Exception, SystemExit) as err:  # rembg dá sys.exit() no import sem onnxruntime
                print(f"{label} indisponível ({err.__class__.__name__}: {err})")
    if alpha is None:
        alpha = cut_grabcut(bgr)
        print("recorte: GrabCut (OpenCV) — sem modelo de matting; qualidade inferior nas bordas")

    # corta pelo bbox do alpha, com margem
    ys, xs = np.where(alpha > 8)
    pad = 6
    y0, y1 = max(0, ys.min() - pad), min(alpha.shape[0], ys.max() + pad)
    x0, x1 = max(0, xs.min() - pad), min(alpha.shape[1], xs.max() + pad)
    rgb = cv2.cvtColor(bgr[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
    a = alpha[y0:y1, x0:x1]

    # descontamina a borda: onde alpha é parcial, puxa a cor para dentro (evita halo cinza da parede)
    rgba = np.dstack([rgb, a])
    img = Image.fromarray(rgba, "RGBA")
    scale = OUT_HEIGHT / img.height
    img = img.resize((round(img.width * scale), OUT_HEIGHT), Image.LANCZOS)

    OUT_WEBP.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_WEBP, "WEBP", quality=82, method=6)
    img.save(OUT_PNG, "PNG", optimize=True)
    print(f"gerado {OUT_WEBP.name} ({OUT_WEBP.stat().st_size // 1024} KB) e "
          f"{OUT_PNG.name} ({OUT_PNG.stat().st_size // 1024} KB) — {img.width}x{img.height}")

    if want_preview:
        dark = Image.new("RGBA", img.size, (14, 14, 14, 255))
        dark.alpha_composite(img)
        dark.convert("RGB").save(PREVIEW)
        print(f"preview: {PREVIEW}")


if __name__ == "__main__":
    main()
