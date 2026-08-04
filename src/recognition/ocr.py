"""
Reconocimiento de valores numéricos en las regiones detectadas (paso 4).

Toma cada región recortada (sobre todo dígitos manuscritos de los totales y
de la tabla de resultados) y devuelve el texto/número reconocido.

Backends soportados (se elige el primero disponible):
    1. easyocr   -> bueno con manuscrito, sin instalar binarios del sistema
    2. pytesseract -> requiere el binario tesseract instalado

Uso (import):
    from ocr import OCR
    ocr = OCR()
    valor = ocr.leer_numero(crop_bgr)
"""
from __future__ import annotations

import logging
import re

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ocr")


class OCR:
    def __init__(self, backend: str | None = None, idiomas=("es",)):
        self.backend = backend or self._autodetect()
        self._reader = None
        if self.backend == "easyocr":
            import easyocr  # type: ignore
            # GPU automática: si el torch instalado tiene CUDA y hay una GPU
            # NVIDIA, EasyOCR corre en ella (el OCR es el 84% del tiempo del
            # pipeline; en GPU acelera varias veces). Con torch CPU-only o sin
            # GPU, cae a CPU sin cambiar nada más. Nota: con GPU basta UN
            # proceso (la GPU ya paraleliza); no usar --slice en ese caso.
            try:
                import torch  # type: ignore
                usar_gpu = torch.cuda.is_available()
            except ImportError:
                usar_gpu = False
            # allowlist de dígitos en leer_numero; aquí cargamos el reader
            self._reader = easyocr.Reader(list(idiomas), gpu=usar_gpu)
            log.info("EasyOCR en %s", "GPU (CUDA)" if usar_gpu else "CPU")
        log.info("OCR backend = %s", self.backend)

    @staticmethod
    def _autodetect() -> str:
        try:
            import easyocr  # noqa: F401
            return "easyocr"
        except ImportError:
            pass
        try:
            import pytesseract  # noqa: F401
            return "pytesseract"
        except ImportError:
            raise SystemExit("Instala easyocr (pip install easyocr) o pytesseract.")

    def _leer_raw(self, crop: np.ndarray, solo_digitos: bool) -> str:
        if self.backend == "easyocr":
            allow = "0123456789" if solo_digitos else None
            res = self._reader.readtext(crop, detail=0, allowlist=allow)
            return " ".join(res)
        # pytesseract
        import pytesseract
        cfg = "--psm 7 -c tessedit_char_whitelist=0123456789" if solo_digitos else "--psm 6"
        return pytesseract.image_to_string(crop, config=cfg)

    def leer_numero(self, crop: np.ndarray) -> int | None:
        """Devuelve el entero reconocido en el recorte, o None si no hay dígitos."""
        txt = self._leer_raw(crop, solo_digitos=True)
        digs = re.sub(r"\D", "", txt)
        return int(digs) if digs else None

    def leer_texto(self, crop: np.ndarray) -> str:
        return self._leer_raw(crop, solo_digitos=False).strip()
