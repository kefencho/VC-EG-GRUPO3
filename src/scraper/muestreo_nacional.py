"""
Muestreo ALEATORIO NACIONAL de actas de escrutinio ONPE EG2026 (1ª vuelta).

Motivación (validez estadística del paper):
    El piloto usó las mesas 000001-000010, todas de un mismo distrito
    (Chachapoyas) → muestra sesgada, no sirve para inferencia. Para el paper,
    la muestra debe ser aleatoria y representativa del universo nacional.

Diseño muestral:
    - Universo: códigos de mesa 1..MAX_MESA (≈88,064, hallado por búsqueda
      binaria sobre el portal el 03-jul-2026).
    - Muestreo aleatorio simple SIN reemplazo, con SEMILLA FIJA PUBLICADA
      (reproducibilidad: cualquiera regenera la misma muestra).
    - Se conserva solo la elección presidencial (idEleccion=10) en estado
      "Contabilizada" (codigoEstadoActa == "C").
    - Se registra la geografía (idUbigeo) de cada acta para reportar la
      cobertura departamental alcanzada (evidencia de representatividad).

Salidas:
    - PDFs en data/muestra/raw_pdf/
    - Ground truth (votos oficiales) en data/muestra/ground_truth/<mesa>.json
    - Manifiesto reproducible data/muestra/muestra.json con: semilla, N,
      MAX_MESA, lista de códigos sorteados, geografía y estado de cada uno.

Uso:
    python muestreo_nacional.py --n 100 --seed 2026 --out ../../data/muestra
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import time
from pathlib import Path

from download_actas import (_session, _get, BACKEND, DELAY_RANGE,
                            obtener_archivo_escrutinio, obtener_url_firmada,
                            _HAS_CFFI, IMPERSONATE)
from ground_truth import ground_truth_mesa

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("muestreo")

ID_PRESIDENCIAL = 10
MAX_MESA_DEFAULT = 88064  # hallado por búsqueda binaria en el portal (03-jul-2026)


def buscar_presidencial_contabilizada(session, mesa: str) -> dict | None:
    r = _get(session, f"{BACKEND}/actas/buscar/mesa",
             params={"codigoMesa": mesa, "idEleccion": ID_PRESIDENCIAL})
    if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
        return None
    actas = (r.json() or {}).get("data") or []
    for a in actas:
        if a.get("idEleccion") == ID_PRESIDENCIAL and a.get("codigoEstadoActa") == "C":
            return a
    return None


def descargar_pdf(session, acta: dict, mesa: str, out_pdf: Path) -> str:
    """Descarga el PDF del acta de escrutinio. Devuelve estado."""
    destino = out_pdf / f"acta_presidencial_{mesa}.pdf"
    if destino.exists():
        return "omitido"
    archivo = obtener_archivo_escrutinio(session, acta["id"])
    if not archivo:
        return "sin_archivo"
    url = obtener_url_firmada(session, archivo["id"])
    if not url:
        return "sin_url"
    r = session.get(url, impersonate=IMPERSONATE, timeout=60) if _HAS_CFFI \
        else session.get(url, timeout=60)
    if r.status_code == 200 and r.content[:4] == b"%PDF":
        destino.write_bytes(r.content)
        return "ok"
    return f"error_{r.status_code}"


def correr(n: int, seed: int, max_mesa: int, out: Path):
    raw_pdf = out / "raw_pdf"
    gt_dir = out / "ground_truth"
    raw_pdf.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    session = _session()
    rng = random.Random(seed)  # generador propio, no toca el global

    seleccionados = []
    intentos = 0
    codigos_vistos = set()
    log.info("Muestreo aleatorio: n=%s seed=%s universo=1..%s", n, seed, max_mesa)

    while len(seleccionados) < n:
        code = rng.randint(1, max_mesa)
        if code in codigos_vistos:
            continue
        codigos_vistos.add(code)
        intentos += 1
        mesa = str(code).zfill(6)

        acta = buscar_presidencial_contabilizada(session, mesa)
        if not acta:
            time.sleep(rng.uniform(*DELAY_RANGE))
            continue

        estado_pdf = descargar_pdf(session, acta, mesa, raw_pdf)
        gt = ground_truth_mesa(session, mesa, ID_PRESIDENCIAL)
        if gt:
            (gt_dir / f"{mesa}.json").write_text(
                json.dumps(gt, ensure_ascii=False, indent=2), encoding="utf-8")

        seleccionados.append({
            "mesa": mesa,
            "codigo": code,
            "id_acta": acta["id"],
            "id_ubigeo": acta.get("idUbigeo"),
            "departamento_ubigeo": str(acta.get("idUbigeo", ""))[:2],
            "local": acta.get("nombreLocalVotacion"),
            "total_electores": acta.get("totalElectoresHabiles"),
            "estado_pdf": estado_pdf,
            "tiene_gt": bool(gt),
        })
        log.info("[%s/%s] mesa %s (ubigeo %s) pdf=%s gt=%s",
                 len(seleccionados), n, mesa, acta.get("idUbigeo"),
                 estado_pdf, bool(gt))
        time.sleep(rng.uniform(*DELAY_RANGE))

    # cobertura departamental alcanzada
    deps: dict[str, int] = {}
    for s in seleccionados:
        d = s["departamento_ubigeo"]
        deps[d] = deps.get(d, 0) + 1

    manifiesto = {
        "seed": seed,
        "n_objetivo": n,
        "n_obtenido": len(seleccionados),
        "max_mesa": max_mesa,
        "codigos_probados": intentos,
        "tasa_acierto": round(len(seleccionados) / intentos, 3) if intentos else 0,
        "departamentos_ubigeo_cubiertos": len(deps),
        "distribucion_departamental": dict(sorted(deps.items())),
        "pdf_ok": sum(1 for s in seleccionados if s["estado_pdf"] in ("ok", "omitido")),
        "con_ground_truth": sum(1 for s in seleccionados if s["tiene_gt"]),
        "actas": seleccionados,
    }
    (out / "muestra.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("=" * 60)
    log.info("Muestra lista: %s actas | %s departamentos | PDF ok=%s | GT=%s",
             len(seleccionados), len(deps), manifiesto["pdf_ok"],
             manifiesto["con_ground_truth"])
    log.info("Manifiesto: %s", out / "muestra.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="tamaño de muestra")
    ap.add_argument("--seed", type=int, default=2026, help="semilla (reproducibilidad)")
    ap.add_argument("--max-mesa", type=int, default=MAX_MESA_DEFAULT)
    ap.add_argument("--out", type=Path, default=Path("../../data/muestra"))
    args = ap.parse_args()
    correr(args.n, args.seed, args.max_mesa, args.out)


if __name__ == "__main__":
    main()
