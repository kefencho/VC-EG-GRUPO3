"""
Extracción del GROUND TRUTH oficial desde la API de la ONPE.

Sustento:
    El mismo portal que publica el PDF del acta publica también los votos ya
    digitados oficialmente (endpoint /actas/buscar/mesa). Ese JSON es la
    "verdad de terreno" del proyecto: permite evaluar el OCR del pipeline
    (exactitud por campo, CER) SIN anotación manual, comparando lo que el
    sistema lee del PDF contra lo que la ONPE registró para la misma mesa.

Genera por mesa un JSON:
    data/ground_truth/000001.json
    {
      "mesa": "000001",
      "votos_partido": {"01": 4, "02": 1, ...},   # por posición en el acta
      "votos_blancos": 29, "votos_nulos": 17, "votos_impugnados": 0,
      "total_emitidos": 180, "total_electores": 230, ...
    }

Uso:
    python ground_truth.py --max 10 --out ../../data/ground_truth
"""
from __future__ import annotations

import argparse
import json
import logging
import time
import random
from pathlib import Path

from download_actas import _get, _session, BACKEND, TIPO_ELECCION, DELAY_RANGE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ground_truth")


def ground_truth_mesa(session, mesa: str, id_eleccion: int) -> dict | None:
    """Convierte la respuesta de la API en el ground truth plano de una mesa."""
    r = _get(session, f"{BACKEND}/actas/buscar/mesa",
             params={"codigoMesa": mesa, "idEleccion": id_eleccion})
    if r.status_code != 200:
        return None
    actas = (r.json() or {}).get("data") or []
    acta = next((a for a in actas if a.get("idEleccion") == id_eleccion), None)
    if not acta:
        return None

    gt = {
        "mesa": mesa,
        "id_acta": acta.get("id"),
        "estado_acta": acta.get("descripcionEstadoActa"),
        "total_electores": acta.get("totalElectoresHabiles"),
        "total_emitidos": acta.get("totalVotosEmitidos"),
        "total_validos": acta.get("totalVotosValidos"),
        "total_asistentes": acta.get("totalAsistentes"),
        "votos_partido": {},   # clave = posición de la fila en el acta (adPosicion)
        "partidos": {},        # posición -> nombre (para reportes legibles)
    }
    # El detalle trae una entrada por organización política con su fila en el
    # acta (adPosicion) y sus votos oficiales (adVotos). Los votos en
    # blanco/nulos/impugnados llegan como entradas especiales; se detectan por
    # descripción para no depender de códigos internos.
    for d in acta.get("detalle") or []:
        desc = (d.get("adDescripcion") or "").upper()
        votos = d.get("adVotos")
        if "BLANCO" in desc:
            gt["votos_blancos"] = votos
        elif "NULO" in desc:
            gt["votos_nulos"] = votos
        elif "IMPUGNADO" in desc:
            gt["votos_impugnados"] = votos
        else:
            pos = d.get("adPosicion")
            if pos is not None:
                gt["votos_partido"][f"{int(pos):02d}"] = votos
                gt["partidos"][f"{int(pos):02d}"] = d.get("adDescripcion")
    return gt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipo", default="presidencial", choices=list(TIPO_ELECCION))
    ap.add_argument("--inicio", type=int, default=1)
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--out", type=Path, default=Path("../../data/ground_truth"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    session = _session()
    id_eleccion = TIPO_ELECCION[args.tipo]
    ok = 0
    for n in range(args.inicio, args.inicio + args.max):
        mesa = str(n).zfill(6)
        gt = ground_truth_mesa(session, mesa, id_eleccion)
        if gt:
            (args.out / f"{mesa}.json").write_text(
                json.dumps(gt, ensure_ascii=False, indent=2), encoding="utf-8")
            ok += 1
            log.info("OK mesa %s (blancos=%s nulos=%s emitidos=%s)",
                     mesa, gt.get("votos_blancos"), gt.get("votos_nulos"),
                     gt.get("total_emitidos"))
        else:
            log.warning("Sin ground truth para mesa %s", mesa)
        time.sleep(random.uniform(*DELAY_RANGE))
    log.info("Ground truth de %s mesas en %s", ok, args.out)


if __name__ == "__main__":
    main()
