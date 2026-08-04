"""
Re-evaluación de salidas OCR ya generadas, con regla de dominio opcional.

Sustento (hallazgo del piloto): en varias actas los miembros de mesa DEJAN LA
CELDA VACÍA en lugar de escribir "0" (p. ej. mesa 000002). El OCR devuelve
null en esas celdas y la evaluación lo cuenta como error contra el 0 oficial,
pero no es un fallo de lectura: es la semántica del formulario. La regla de
dominio "celda de votos sin trazo = 0" (null -> 0) se aplica SOLO a los campos
de votos por organización política y a votos impugnados (los campos de
totales y blancos/nulos siempre se escriben), y se reporta por separado para
no mezclar mejoras de visión con reglas de negocio.

Uso:
    python evaluar_salidas.py --salidas ../../data/salida_final \
        --gt ../../data/ground_truth --regla-cero
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.piloto_10_actas import evaluar_acta  # noqa: E402


def aplicar_regla_cero(pred: dict) -> dict:
    """Celda de votos sin lectura -> 0 (semántica del formulario)."""
    pred = json.loads(json.dumps(pred))  # copia
    pred["votos_partido"] = {k: (0 if v is None else v)
                             for k, v in pred["votos_partido"].items()}
    if pred.get("votos_impugnados") is None:
        pred["votos_impugnados"] = 0
    return pred


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salidas", type=Path, default=Path("../../data/salida_final"))
    ap.add_argument("--gt", type=Path, default=Path("../../data/ground_truth"))
    ap.add_argument("--regla-cero", action="store_true")
    ap.add_argument("--out", type=Path, default=None,
                    help="si se indica, guarda el JSON de evaluación ahí")
    args = ap.parse_args()

    tot_campos = tot_ok = 0
    cers = []
    actas = []
    for pred_path in sorted(args.salidas.glob("*.json")):
        if pred_path.name == "evaluacion.json":
            continue
        gt_path = args.gt / pred_path.name
        if not gt_path.exists():
            continue
        pred = json.loads(pred_path.read_text(encoding="utf-8"))
        if args.regla_cero:
            pred = aplicar_regla_cero(pred)
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        ev = evaluar_acta(pred, gt)
        ev["mesa"] = pred_path.stem
        actas.append(ev)
        tot_campos += ev["campos_evaluados"]
        tot_ok += ev["campos_correctos"]
        cers.append(ev["cer_promedio"])
        print(f"mesa {ev['mesa']}: {ev['campos_correctos']}/{ev['campos_evaluados']} "
              f"({100 * ev['exactitud_campo']:.0f}%) CER={ev['cer_promedio']}")

    n = len(actas)
    totales = {
        "actas_evaluadas": n,
        "exactitud_campo_global": round(tot_ok / tot_campos, 4) if tot_campos else 0,
        "campos_evaluados": tot_campos,
        "campos_correctos": tot_ok,
        "cer_promedio_global": round(sum(cers) / n, 4) if n else 0,
        "actas_perfectas": sum(1 for a in actas if a["acta_perfecta"]),
        "regla_cero": args.regla_cero,
    }
    print("TOTALES:", totales)
    if args.out:
        args.out.write_text(json.dumps({"actas": actas, "totales": totales},
                                       ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
