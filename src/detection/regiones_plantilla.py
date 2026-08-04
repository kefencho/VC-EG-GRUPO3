"""
Detección de regiones de interés por PLANTILLA (etapa 3 del pipeline — piloto).

Sustento del enfoque:
    El acta de escrutinio de la ONPE es un formulario de LAYOUT FIJO: todas las
    actas del proceso EG2026 se generan con la misma plantilla (misma posición
    de la tabla de votos, totales, mesa y observaciones), e incluyen marcas
    fiduciales en las esquinas. Por eso, para el piloto de viabilidad, las
    regiones se definen UNA sola vez como fracciones (0..1) del ancho/alto de
    la página y se propagan a todas las actas después del deskew del
    preprocesamiento. Esto entrega recortes exactos con costo de anotación
    casi cero.

    Se usan fracciones y no píxeles para que el mismo código funcione a
    cualquier DPI de rasterizado (el piloto usa 300 DPI ≈ 3509x4963 px).

Calibración:
    Las fracciones se calibraron visualmente sobre el acta de la mesa 000001
    (data/processed/acta_presidencial_000001.png) y se verifican con el modo
    --debug, que dibuja todas las cajas sobre el acta para inspección ocular.

Uso:
    # ver la plantilla dibujada sobre un acta (calibración)
    python regiones_plantilla.py --debug --img ../../data/processed/acta_presidencial_000001.png

    # recortar los campos de todas las actas procesadas
    python regiones_plantilla.py --in ../../data/processed --out ../../data/crops
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("regiones_plantilla")

# --------------------------------------------------------------------------- #
# Plantilla de regiones (fracciones del ancho/alto de la página)
# Calibrada sobre el acta presidencial EG2026 a 300 DPI (mesa 000001).
# --------------------------------------------------------------------------- #

# La columna "TOTAL DE VOTOS" es una franja vertical con una celda por fila.
# Las 38 filas de organizaciones políticas son equiespaciadas; debajo siguen
# 4 filas de resumen con la misma altura.
COL_VOTOS_X1 = 0.455   # borde izquierdo de la celda de votos
COL_VOTOS_X2 = 0.549   # borde derecho
FILA1_Y = 0.2140       # borde superior de la fila 1
ALTO_FILA = 0.01655    # alto de cada fila (38 filas + 4 de resumen)
N_PARTIDOS = 38

# Campos únicos (x1, y1, x2, y2) en fracciones de página
CAMPOS_FIJOS = {
    "numero_mesa":         (0.058, 0.095, 0.198, 0.121),
    "total_electores":     (0.865, 0.103, 0.945, 0.123),
    "total_ciudadanos":    (0.270, 0.918, 0.362, 0.942),
    "observaciones":       (0.088, 0.948, 0.795, 0.995),
}

# --------------------------------------------------------------------------- #
# Registro por marcas fiduciales (alineación previa al recorte)
#
# Sustento: la evaluación nacional mostró que algunos escaneos traen bandas
# negras del escáner o desplazamientos de encuadre (p. ej. mesa 084786,
# corrida ~184 px hacia abajo), con lo que las fracciones fijas caen en la
# fila equivocada. El propio formulario trae la solución: cuadrados negros
# de registro (fiduciales) impresos en el borde. Se detectan, se emparejan
# con sus posiciones de referencia (calibradas en la mesa 000001) usando
# RANSAC de traslación —robusto a marcas faltantes y a falsos positivos como
# los dígitos de muestra "0123456789"— y se estima una transformación afín
# parcial que lleva el acta al marco de referencia antes de recortar.
# --------------------------------------------------------------------------- #

# Posiciones (fx, fy) de las 15 marcas fiduciales del acta de referencia
# (mesa 000001 procesada a 300 DPI, 3509x4963), solo bandas laterales,
# superior e inferior de la página.
REF_FIDUCIALES = [
    (0.0251, 0.0111), (0.0928, 0.0109), (0.4578, 0.0108), (0.5469, 0.0108),
    (0.9782, 0.0104),
    (0.0248, 0.2111), (0.9785, 0.2111),
    (0.0236, 0.5424), (0.9772, 0.5424),
    (0.0239, 0.8424), (0.9766, 0.8400),
    (0.0242, 0.8923), (0.9775, 0.8895),
    (0.0249, 0.9848), (0.9785, 0.9809),
]
REF_W, REF_H = 3509, 4963  # marco de referencia (300 DPI)


def detectar_fiduciales(gray):
    """
    Detecta candidatos a marca fiducial: componentes conexos oscuros,
    cuadrados (aspecto ~1, relleno alto), en las bandas del borde de página.
    Devuelve centroides en píxeles.
    """
    h, w = gray.shape[:2]
    _, bw = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    n, _, stats, cents = cv2.connectedComponentsWithStats(bw, 8)
    puntos = []
    for i in range(1, n):
        x, y, ww, hh, area = stats[i]
        if not (800 < area < 12000):
            continue
        if not (0.6 < ww / hh < 1.6):
            continue
        if area / (ww * hh) < 0.75:
            continue
        cx, cy = cents[i]
        fx, fy = cx / w, cy / h
        # bandas del borde (tolerantes al desplazamiento del escaneo)
        if fx < 0.07 or fx > 0.93 or fy < 0.10 or fy > 0.94:
            puntos.append((float(cx), float(cy)))
    return puntos


def alinear_por_fiduciales(img, umbral_px: int = 30, min_inliers: int = 4):
    """
    Lleva el acta al marco de referencia (REF_W x REF_H) alineando sus marcas
    fiduciales con las de la plantilla. Si no hay suficientes marcas
    confiables, devuelve la imagen sin tocar (mejor no alinear que alinear mal).
    """
    import numpy as np
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    detectados = detectar_fiduciales(gray)
    if len(detectados) < min_inliers:
        return img

    ref = [(fx * REF_W, fy * REF_H) for fx, fy in REF_FIDUCIALES]

    # RANSAC de traslación: cada par (detectado, referencia) propone un
    # desplazamiento; gana el que más marcas deja emparejadas.
    mejor_pares = []
    for tx, ty in detectados:
        for rx, ry in ref:
            dx, dy = rx - tx, ry - ty
            pares = []
            usados = set()
            for px, py in detectados:
                qx, qy = px + dx, py + dy
                mejor_j, mejor_d = None, umbral_px
                for j, (ax, ay) in enumerate(ref):
                    if j in usados:
                        continue
                    d = max(abs(qx - ax), abs(qy - ay))
                    if d < mejor_d:
                        mejor_j, mejor_d = j, d
                if mejor_j is not None:
                    usados.add(mejor_j)
                    pares.append(((px, py), ref[mejor_j]))
            if len(pares) > len(mejor_pares):
                mejor_pares = pares

    if len(mejor_pares) < min_inliers:
        return img

    src = np.array([p[0] for p in mejor_pares], dtype=np.float32)
    dst = np.array([p[1] for p in mejor_pares], dtype=np.float32)
    M, _ = cv2.estimateAffinePartial2D(src, dst, ransacReprojThreshold=8)
    if M is None:
        return img
    return cv2.warpAffine(img, M, (REF_W, REF_H), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)

# Filas de resumen que siguen a las 38 de partidos (comparten la columna de votos)
FILAS_RESUMEN = ["votos_blancos", "votos_nulos", "votos_impugnados", "total_emitidos"]


def _abs(box, w, h):
    """Convierte una caja fraccional a píxeles absolutos."""
    x1, y1, x2, y2 = box
    return int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)


def regiones(w: int, h: int) -> dict[str, tuple[int, int, int, int]]:
    """
    Devuelve TODAS las regiones de la plantilla en píxeles para una imagen
    de tamaño (w, h): campos fijos + celda de votos de cada partido (1..38)
    + filas de resumen.
    """
    reg = {n: _abs(b, w, h) for n, b in CAMPOS_FIJOS.items()}
    for i in range(N_PARTIDOS):
        y1 = FILA1_Y + i * ALTO_FILA
        reg[f"votos_partido_{i + 1:02d}"] = _abs(
            (COL_VOTOS_X1, y1, COL_VOTOS_X2, y1 + ALTO_FILA), w, h)
    for j, nombre in enumerate(FILAS_RESUMEN):
        y1 = FILA1_Y + (N_PARTIDOS + j) * ALTO_FILA
        reg[nombre] = _abs((COL_VOTOS_X1, y1, COL_VOTOS_X2, y1 + ALTO_FILA), w, h)
    return reg


def recortar_acta(img_path: Path, out_dir: Path, alinear: bool = True) -> dict:
    """Recorta todas las regiones de un acta y las guarda como PNG individuales."""
    img = cv2.imread(str(img_path))
    if img is None:
        raise FileNotFoundError(img_path)
    if alinear:
        img = alinear_por_fiduciales(img)
    h, w = img.shape[:2]
    destino = out_dir / img_path.stem
    destino.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for nombre, (x1, y1, x2, y2) in regiones(w, h).items():
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        ruta = destino / f"{nombre}.png"
        cv2.imwrite(str(ruta), crop)
        manifest[nombre] = [x1, y1, x2, y2]
    (destino / "regiones.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def dibujar_debug(img_path: Path, out_path: Path, alinear: bool = True):
    """Dibuja la plantilla sobre el acta para verificar la calibración a ojo."""
    img = cv2.imread(str(img_path))
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if alinear:
        img = alinear_por_fiduciales(img)
    h, w = img.shape[:2]
    for nombre, (x1, y1, x2, y2) in regiones(w, h).items():
        color = (0, 0, 255) if not nombre.startswith("votos_partido") else (255, 0, 0)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        if not nombre.startswith("votos_partido"):
            cv2.putText(img, nombre, (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    cv2.imwrite(str(out_path), img)
    log.info("Overlay de calibración: %s", out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", type=Path, default=Path("../../data/processed"))
    ap.add_argument("--out", dest="out_dir", type=Path, default=Path("../../data/crops"))
    ap.add_argument("--debug", action="store_true", help="dibuja la plantilla sobre --img")
    ap.add_argument("--img", type=Path, help="imagen para el modo --debug")
    ap.add_argument("--sin-alinear", action="store_true",
                    help="desactiva el registro por fiduciales (solo diagnóstico)")
    args = ap.parse_args()
    alinear = not args.sin_alinear

    if args.debug:
        if not args.img:
            raise SystemExit("--debug requiere --img")
        dibujar_debug(args.img, args.img.with_name(args.img.stem + "_overlay.png"),
                      alinear=alinear)
        return

    imgs = sorted(p for p in args.in_dir.iterdir()
                  if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    log.info("Recortando regiones de %s actas (alinear=%s) -> %s",
             len(imgs), alinear, args.out_dir)
    for p in imgs:
        recortar_acta(p, args.out_dir, alinear=alinear)
        log.info("OK %s", p.name)
    log.info("Listo.")


if __name__ == "__main__":
    main()
