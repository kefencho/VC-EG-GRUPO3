"""
Preprocesamiento de actas de escrutinio (paso 2 del pipeline).

Aplica las operaciones descritas en la propuesta:
    - Corrección de inclinación (deskew)
    - Mejora de contraste (CLAHE)
    - Reducción de ruido
    - Binarización / normalización

Uso (CLI):
    python preprocess.py --in ../../data/raw_img --out ../../data/processed

Uso (import):
    from preprocess import preprocess_image
    img = preprocess_image(ruta_o_array)
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("preprocess")


def deskew(gray: np.ndarray) -> np.ndarray:
    """Corrige la inclinación de la imagen usando el ángulo dominante."""
    inv = cv2.bitwise_not(gray)
    thr = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thr > 0))
    if coords.size == 0:
        return gray
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.1:
        return gray
    (h, w) = gray.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def mejorar_contraste(gray: np.ndarray) -> np.ndarray:
    """CLAHE: ecualización adaptativa para uniformar iluminación."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def reducir_ruido(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)


def binarizar(gray: np.ndarray) -> np.ndarray:
    """Binarización adaptativa, robusta ante sombras y sellos."""
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, blockSize=35, C=11)


def preprocess_image(src, binariza: bool = False) -> np.ndarray:
    """
    Pipeline de preprocesamiento.

    src: ruta (str/Path) o imagen np.ndarray (BGR o gris).
    binariza: si True devuelve imagen binaria; si False, gris realzado
              (mejor para modelos de detección que esperan 3 canales).
    """
    if isinstance(src, (str, Path)):
        img = cv2.imread(str(src))
        if img is None:
            raise FileNotFoundError(src)
    else:
        img = src
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    gray = deskew(gray)
    gray = mejorar_contraste(gray)
    gray = reducir_ruido(gray)
    if binariza:
        return binarizar(gray)
    return gray


def correr(in_dir: Path, out_dir: Path, binariza: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    imgs = [p for p in in_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    log.info("Preprocesando %s imágenes -> %s", len(imgs), out_dir)
    for p in imgs:
        out = preprocess_image(p, binariza=binariza)
        cv2.imwrite(str(out_dir / p.name), out)
    log.info("Listo.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", type=Path, default=Path("../../data/raw_img"))
    ap.add_argument("--out", dest="out_dir", type=Path, default=Path("../../data/processed"))
    ap.add_argument("--binariza", action="store_true")
    args = ap.parse_args()
    correr(args.in_dir, args.out_dir, args.binariza)


if __name__ == "__main__":
    main()
