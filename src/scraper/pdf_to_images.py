"""
Convierte los PDF de actas descargados a imágenes PNG (300 DPI) para el
pipeline de visión. Usa PyMuPDF (fitz) que no requiere binarios externos.

Uso:
    python pdf_to_images.py --in ../../data/raw_pdf --out ../../data/raw_img --dpi 300
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("pdf_to_images")


def convertir(in_dir: Path, out_dir: Path, dpi: int = 300):
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise SystemExit("Falta PyMuPDF. Instala: pip install pymupdf") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(in_dir.glob("*.pdf"))
    log.info("Convirtiendo %s PDFs a PNG @ %s DPI", len(pdfs), dpi)
    zoom = dpi / 72.0
    for pdf in pdfs:
        doc = fitz.open(pdf)
        for n, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            nombre = f"{pdf.stem}_p{n}.png" if doc.page_count > 1 else f"{pdf.stem}.png"
            pix.save(out_dir / nombre)
        doc.close()
    # copia las imágenes que ya venían como jpg/png
    for img in list(in_dir.glob("*.jpg")) + list(in_dir.glob("*.png")):
        (out_dir / img.name).write_bytes(img.read_bytes())
    log.info("Imágenes en: %s", out_dir)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_dir", type=Path, default=Path("../../data/raw_pdf"))
    p.add_argument("--out", dest="out_dir", type=Path, default=Path("../../data/raw_img"))
    p.add_argument("--dpi", type=int, default=300)
    args = p.parse_args()
    convertir(args.in_dir, args.out_dir, args.dpi)


if __name__ == "__main__":
    main()
