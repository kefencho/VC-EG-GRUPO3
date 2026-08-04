"""
PILOTO DE VIABILIDAD — 10 actas de punta a punta (etapas 4 y 5 del pipeline).

Toma los recortes generados por la plantilla (etapa 3), reconoce los valores
numéricos con OCR (etapa 4), arma el JSON estructurado por acta (etapa 5) y
EVALÚA contra el ground truth oficial de la ONPE (los votos ya digitados que
publica la propia API del portal), calculando:

    - exactitud por campo (¿el número leído es exactamente el oficial?)
    - exactitud por documento (% de actas con todos los campos correctos)
    - CER global (Character Error Rate sobre las cadenas de dígitos)
    - desglose de errores por tipo de campo, para diagnóstico

Sustento de las decisiones:
    - OCR con allowlist de dígitos (recognition/ocr.py): los campos del acta
      son numéricos; restringir el vocabulario elimina confusiones
      letra/dígito (p. ej. 'O' vs '0').
    - Upscale 2x de cada recorte antes del OCR: las celdas de votos miden
      ~330x80 px a 300 DPI; EasyOCR reconoce mejor los trazos manuscritos
      finos con más resolución aparente.
    - El ground truth viene de la API oficial (scraper/ground_truth.py), no
      de anotación manual: evaluación reproducible y sin sesgo del anotador.

Uso:
    python piloto_10_actas.py --crops ../../data/crops \
        --gt ../../data/ground_truth --out ../../data/salida
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1]))
from recognition.ocr import OCR  # noqa: E402
from utils.metrics import cer  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("piloto")

# Campos numéricos únicos del acta y su clave en el JSON de salida
CAMPOS_UNICOS = {
    "numero_mesa": "mesa_ocr",
    "total_electores": "total_electores",
    "total_ciudadanos": "total_ciudadanos_que_votaron",
    "votos_blancos": "votos_blancos",
    "votos_nulos": "votos_nulos",
    "votos_impugnados": "votos_impugnados",
    "total_emitidos": "total_emitidos",
}
N_PARTIDOS = 38


# Posición (fracción del ancho de la celda) de los separadores punteados que
# dividen la celda de votos en centenas/decenas/unidades. Son fijos en la
# plantilla del acta; se miden sobre la mesa 000001 y se borran por posición.
SEPARADORES_X = (0.31, 0.70)
ANCHO_SEPARADOR = 0.045  # semiancho de la franja a borrar


def limpiar_celda(img: np.ndarray, margen: float = 0.10,
                  con_separadores: bool = True) -> np.ndarray:
    """
    Aísla la tinta del lapicero (mejora v3 del piloto).

    Sustento (análisis de errores de las corridas anteriores):
      1. Los BORDES impresos de la celda se leían como "1"/"4"
         -> se recorta un margen interior (v2).
      2. Los separadores PUNTEADOS internos se leían como dígitos
         ("18"->"418", "22"->"212"). Son tan oscuros como la tinta, así que
         un umbral no los elimina (falla de v2): se BORRAN POR POSICIÓN,
         porque la plantilla del acta los ubica siempre en los mismos
         tercios de la celda (v3).
      3. Las filas sombreadas del formulario dejaban ruido con umbral fijo
         -> umbral de OTSU por celda + filtro de motas pequeñas (v3).
    """
    h, w = img.shape[:2]
    mx, my = int(w * margen), int(h * margen)
    img = img[my:h - my, mx:w - mx]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img

    # binarización adaptativa por celda (robusta al sombreado alterno de filas)
    _, tinta = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    # borra las franjas de los separadores punteados (posición de plantilla)
    if con_separadores:
        hw = tinta.shape[1]
        for fx in SEPARADORES_X:
            x1 = max(0, int((fx - ANCHO_SEPARADOR) * hw))
            x2 = min(hw, int((fx + ANCHO_SEPARADOR) * hw))
            tinta[:, x1:x2] = 0

    # filtro de motas: elimina componentes conexos demasiado pequeños para
    # ser un trazo (restos de trama, puntos sueltos de la digitalización)
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(tinta, 8)
    min_area = max(30, int(0.002 * tinta.size))
    limpio = np.full_like(gray, 255)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            limpio[etiquetas == i] = 0
    return limpio


def leer_campo(ocr: OCR, ruta: Path, modo: str = "limpio",
               sub_cajas: int = 1) -> int | None:
    """
    OCR de un recorte con upscale (las celdas miden ~330x80 px a 300 DPI).

    modo "basico": lee el recorte tal cual (línea base del piloto).
    modo "limpio": aísla la tinta antes de leer; si el campo tiene casillas
      impresas por dígito (sub_cajas>1), se lee casilla por casilla y se
      concatena — así los bordes internos no se cuelan en la lectura.
    Si la lectura limpia falla (trazo muy tenue eliminado por el umbral),
    se reintenta con el recorte original como respaldo.
    """
    img = cv2.imread(str(ruta))
    if img is None:
        return None

    def _ocr(arr) -> int | None:
        arr = cv2.resize(arr, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        return ocr.leer_numero(arr)

    if modo == "basico":
        return _ocr(img)

    if sub_cajas > 1:
        h, w = img.shape[:2]
        digitos = []
        for k in range(sub_cajas):
            caja = img[:, k * w // sub_cajas:(k + 1) * w // sub_cajas]
            d = _ocr(limpiar_celda(caja, margen=0.18))
            if d is not None:
                digitos.append(str(d))
        if digitos:
            return int("".join(digitos))
        return _ocr(limpiar_celda(img))

    valor = _ocr(limpiar_celda(img))
    if valor is None:
        valor = _ocr(img)  # respaldo: quizá el umbral borró un trazo tenue
    return valor


# Campos cuyo valor está en casillas impresas separadas (una por dígito)
SUB_CAJAS = {"total_ciudadanos": 3}


def procesar_acta(ocr: OCR, carpeta: Path, modo: str = "limpio") -> dict:
    """Etapas 4-5 para un acta: OCR de cada recorte -> JSON estructurado."""
    salida: dict = {"carpeta": carpeta.name, "votos_partido": {}}
    for campo, clave in CAMPOS_UNICOS.items():
        salida[clave] = leer_campo(ocr, carpeta / f"{campo}.png", modo,
                                   SUB_CAJAS.get(campo, 1))
    for i in range(1, N_PARTIDOS + 1):
        salida["votos_partido"][f"{i:02d}"] = leer_campo(
            ocr, carpeta / f"votos_partido_{i:02d}.png", modo)
    return salida


def evaluar_acta(pred: dict, gt: dict) -> dict:
    """Compara la lectura OCR contra el ground truth oficial de la mesa."""
    comparaciones = []  # (campo, oficial, leido)

    # votos por organización política: solo las posiciones que existen en el
    # acta según la ONPE. Las filas vacías del formulario (posiciones 04 y 14,
    # partidos retirados) vienen con votos null en la API y NO se evalúan:
    # contarlas inflaría la exactitud (null OCR == null oficial es un acierto
    # espurio, no una lectura).
    for pos, oficial in (gt.get("votos_partido") or {}).items():
        if oficial is None:
            continue
        comparaciones.append((f"partido_{pos}", oficial,
                              pred["votos_partido"].get(pos)))

    mapa_unicos = [
        ("votos_blancos", gt.get("votos_blancos"), pred.get("votos_blancos")),
        ("votos_nulos", gt.get("votos_nulos"), pred.get("votos_nulos")),
        ("votos_impugnados", gt.get("votos_impugnados"), pred.get("votos_impugnados")),
        ("total_emitidos", gt.get("total_emitidos"), pred.get("total_emitidos")),
        ("total_electores", gt.get("total_electores"), pred.get("total_electores")),
        ("numero_mesa", int(gt["mesa"]), pred.get("mesa_ocr")),
        ("total_ciudadanos", gt.get("total_asistentes"),
         pred.get("total_ciudadanos_que_votaron")),
    ]
    comparaciones.extend((c, o, l) for c, o, l in mapa_unicos if o is not None)

    errores = [{"campo": c, "oficial": o, "leido": l}
               for c, o, l in comparaciones if str(o) != str(l)]
    n = len(comparaciones)
    cer_total = sum(cer(str(o), "" if l is None else str(l))
                    for _, o, l in comparaciones) / n if n else 0.0
    return {
        "campos_evaluados": n,
        "campos_correctos": n - len(errores),
        "exactitud_campo": round((n - len(errores)) / n, 4) if n else 0.0,
        "cer_promedio": round(cer_total, 4),
        "acta_perfecta": not errores,
        "errores": errores,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crops", type=Path, default=Path("../../data/crops"))
    ap.add_argument("--gt", type=Path, default=Path("../../data/ground_truth"))
    ap.add_argument("--out", type=Path, default=Path("../../data/salida"))
    ap.add_argument("--modo", default="limpio", choices=["basico", "limpio"],
                    help="basico = línea base; limpio = aislar tinta + sub-cajas (v2)")
    ap.add_argument("--slice", dest="slice_", default=None,
                    help="k/N: procesa solo las actas con índice %% N == k (OCR paralelo)")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ocr = OCR(idiomas=("es",))

    carpetas = sorted(p for p in args.crops.iterdir() if p.is_dir())
    # OCR paralelo: cada proceso toma una porción disjunta de las actas.
    if args.slice_:
        k, tot = (int(x) for x in args.slice_.split("/"))
        carpetas = [c for i, c in enumerate(carpetas) if i % tot == k]
        log.info("Slice %s: %s actas de este proceso", args.slice_, len(carpetas))
    else:
        log.info("Piloto sobre %s actas", len(carpetas))

    resumen = {"actas": [], "totales": {}}
    tot_campos = tot_ok = 0
    cers = []
    for carpeta in carpetas:
        mesa = carpeta.name.split("_")[-1]
        pred = procesar_acta(ocr, carpeta, args.modo)
        (args.out / f"{mesa}.json").write_text(
            json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8")

        gt_path = args.gt / f"{mesa}.json"
        if not gt_path.exists():
            log.warning("Mesa %s sin ground truth; se omite la evaluación", mesa)
            continue
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        ev = evaluar_acta(pred, gt)
        ev["mesa"] = mesa
        resumen["actas"].append(ev)
        tot_campos += ev["campos_evaluados"]
        tot_ok += ev["campos_correctos"]
        cers.append(ev["cer_promedio"])
        log.info("Mesa %s: %s/%s campos correctos (%.1f%%), CER=%.3f",
                 mesa, ev["campos_correctos"], ev["campos_evaluados"],
                 100 * ev["exactitud_campo"], ev["cer_promedio"])

    n_actas = len(resumen["actas"])
    resumen["totales"] = {
        "actas_evaluadas": n_actas,
        "exactitud_campo_global": round(tot_ok / tot_campos, 4) if tot_campos else 0,
        "campos_evaluados": tot_campos,
        "campos_correctos": tot_ok,
        "cer_promedio_global": round(sum(cers) / n_actas, 4) if n_actas else 0,
        "actas_perfectas": sum(1 for a in resumen["actas"] if a["acta_perfecta"]),
        "segundos_totales": round(time.time() - t0, 1),
    }
    # con --slice cada proceso escribiría el mismo evaluacion.json (colisión);
    # los JSON por acta ya quedaron escritos y evaluar_salidas.py da el total.
    if not args.slice_:
        (args.out / "evaluacion.json").write_text(
            json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    t = resumen["totales"]
    log.info("=" * 60)
    log.info("RESULTADO PILOTO: %s/%s campos correctos (%.2f%%) | CER=%.4f | "
             "actas perfectas: %s/%s | %.1f s",
             t["campos_correctos"], t["campos_evaluados"],
             100 * t["exactitud_campo_global"], t["cer_promedio_global"],
             t["actas_perfectas"], t["actas_evaluadas"], t["segundos_totales"])
    log.info("Detalle: %s", args.out / "evaluacion.json")


if __name__ == "__main__":
    main()
