"""
Extracción de actas ELECTRÓNICAS (STAE) por capa de texto — sin OCR.

Hallazgo del muestreo nacional: ~24% de las actas son documentos electrónicos
firmados digitalmente (STAE), con los votos IMPRESOS y una capa de texto PDF
extraíble. No son un problema de visión: se parsean directamente.

Este módulo lo demuestra: extrae los valores de la capa de texto y los compara
contra el ground truth oficial de la API. Sustenta la recomendación práctica
del pipeline final: DETECTAR primero el tipo de acta (texto PDF vs escaneo) y
enrutar — texto → parseo directo (~100%); escaneo → detección + OCR.

Estructura del texto STAE (verificada): cada nombre de organización política
va seguido inmediatamente por su número de votos; los campos de resumen
(VOTOS EN BLANCO/NULOS/IMPUGNADOS, TOTAL DE VOTOS EMITIDOS) igual.

Uso:
    python extraer_electronicas.py --tipos ../../data/muestra/tipos.json \
        --pdf ../../data/muestra/raw_pdf --gt ../../data/muestra/ground_truth \
        --out ../../data/muestra/electronicas.json
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


RESUMEN = {
    "VOTOS EN BLANCO": "votos_blancos",
    "VOTOS NULOS": "votos_nulos",
    "VOTOS IMPUGNADOS": "votos_impugnados",
    "TOTAL DE VOTOS EMITIDOS": "total_emitidos",
}


def extraer_pdf(pdf_path: Path) -> dict:
    """Extrae {nombre_partido_normalizado: votos} y resumen de un PDF STAE."""
    import fitz
    doc = fitz.open(pdf_path)
    lineas = []
    for pg in doc:
        lineas += [l.strip() for l in pg.get_text().splitlines() if l.strip()]
    doc.close()

    valores_partido = {}   # nombre normalizado -> voto
    resumen = {}
    for i, ln in enumerate(lineas[:-1]):
        sig = lineas[i + 1]
        if not re.fullmatch(r"\d{1,3}", sig):
            continue
        clave = norm(ln)
        if clave in {norm(k) for k in RESUMEN}:
            resumen[RESUMEN[[k for k in RESUMEN if norm(k) == clave][0]]] = int(sig)
        elif len(clave) > 6 and not clave.isdigit():
            # nombre de organización política (heurística: texto largo no numérico)
            valores_partido[clave] = int(sig)
    return {"partidos": valores_partido, "resumen": resumen}


def evaluar(extraido: dict, gt: dict) -> dict:
    """Compara lo extraído contra el ground truth oficial de la mesa."""
    comparaciones = []
    # partidos: mapear por nombre normalizado
    gt_por_nombre = {norm(v): gt["votos_partido"].get(pos)
                     for pos, v in (gt.get("partidos") or {}).items()}
    for nombre, oficial in gt_por_nombre.items():
        if oficial is None:
            continue
        leido = extraido["partidos"].get(nombre)
        comparaciones.append((oficial, leido))
    for campo in ("votos_blancos", "votos_nulos", "votos_impugnados", "total_emitidos"):
        if gt.get(campo) is not None:
            comparaciones.append((gt[campo], extraido["resumen"].get(campo)))
    n = len(comparaciones)
    ok = sum(1 for o, l in comparaciones if str(o) == str(l))
    return {"campos": n, "correctos": ok,
            "exactitud": round(ok / n, 4) if n else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipos", type=Path, default=Path("../../data/muestra/tipos.json"))
    ap.add_argument("--pdf", type=Path, default=Path("../../data/muestra/raw_pdf"))
    ap.add_argument("--gt", type=Path, default=Path("../../data/muestra/ground_truth"))
    ap.add_argument("--out", type=Path, default=Path("../../data/muestra/electronicas.json"))
    args = ap.parse_args()

    tipos = json.loads(args.tipos.read_text(encoding="utf-8"))
    electronicas = tipos["electronicas"]

    resultados = []
    tot_c = tot_ok = 0
    for mesa in electronicas:
        pdf = args.pdf / f"acta_presidencial_{mesa}.pdf"
        gt_path = args.gt / f"{mesa}.json"
        if not pdf.exists() or not gt_path.exists():
            continue
        extraido = extraer_pdf(pdf)
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        ev = evaluar(extraido, gt)
        ev["mesa"] = mesa
        resultados.append(ev)
        tot_c += ev["campos"]
        tot_ok += ev["correctos"]
        print(f"mesa {mesa}: {ev['correctos']}/{ev['campos']} ({100*ev['exactitud']:.0f}%)")

    resumen = {
        "n_actas": len(resultados),
        "exactitud_global": round(tot_ok / tot_c, 4) if tot_c else 0,
        "campos": tot_c, "correctos": tot_ok,
        "actas": resultados,
    }
    print("=" * 50)
    print(f"ELECTRÓNICAS: {len(resultados)} actas | "
          f"exactitud extracción por texto = {100*resumen['exactitud_global']:.2f}% "
          f"({tot_ok}/{tot_c} campos)")
    args.out.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
