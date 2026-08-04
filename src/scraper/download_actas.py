"""
Descarga automatizada de Actas de Escrutinio de la ONPE
Elecciones Generales del Perú 2026 - Primera Vuelta.

Endpoints REALES verificados en vivo el 02/07/2026 contra el portal oficial
https://resultadoelectoral.onpe.gob.pe (proceso EG2026, idEleccionPrincipal=10).

Cadena de descarga (así funciona el portal por dentro):
    1. GET /presentacion-backend/actas/buscar/mesa?codigoMesa=NNNNNN&idEleccion=ID
         -> lista de actas de esa mesa (una por tipo de elección:
            10=presidencial, 12..15=congresales/parlamento andino).
    2. GET /presentacion-backend/actas/{idActa}
         -> detalle con data.archivos[]; el archivo tipo=1 es el
            "ACTA DE ESCRUTINIO" (nuestro objetivo), tipo=2 es la de
            instalación y sufragio.
    3. GET /presentacion-backend/actas/file?id={archivoId}
         -> devuelve en data una URL FIRMADA de S3 (expira), desde la cual
            se descarga el PDF real.

Sustento de las decisiones técnicas:
    - curl_cffi con impersonate="chrome124": el portal está detrás de un WAF
      que devuelve la SPA de Angular (HTML) a los clientes HTTP comunes; con
      la huella TLS de Chrome responde JSON. `requests` clásico NO funciona.
    - Headers Referer/X-Requested-With/Accept-Language: imitan a la SPA real
      para no ser filtrados.
    - Delay aleatorio entre mesas (1.0-2.5 s): cortesía con el servidor
      público y menor riesgo de bloqueo por tasa.
    - Los códigos de mesa son secuenciales desde 000001; se filtra por
      estado "Contabilizada" para asegurar que el acta tenga imagen final.
    - Manifest CSV: registra cada intento (ok/error) para poder reanudar la
      descarga sin repetir trabajo (los PDF existentes se omiten).

Uso:
    python download_actas.py --max 10 --out ../../data/raw_pdf
    python download_actas.py --tipo presidencial --inicio 1 --max 10
"""
from __future__ import annotations

import argparse
import csv
import logging
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from curl_cffi import requests as cffi_requests
    _HAS_CFFI = True
except ImportError:  # sin curl_cffi el WAF bloquea; se avisa y se intenta igual
    import requests as cffi_requests  # type: ignore
    _HAS_CFFI = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("download_actas")

# --------------------------------------------------------------------------- #
# Configuración de endpoints ONPE (verificados 02/07/2026)
# --------------------------------------------------------------------------- #
BASE_URL = "https://resultadoelectoral.onpe.gob.pe"
BACKEND = f"{BASE_URL}/presentacion-backend"

# idEleccion observados en las actas de cada mesa del proceso EG2026.
# 10 es la elección principal (presidencial) según proceso-electoral-activo.
TIPO_ELECCION = {
    "presidencial": 10,
    "eleccion_12": 12,
    "eleccion_13": 13,
    "eleccion_14": 14,
    "eleccion_15": 15,
}

# tipo de archivo dentro del acta: 1 = ACTA DE ESCRUTINIO (la que contiene
# los votos manuscritos), 2 = ACTA DE INSTALACIÓN Y SUFRAGIO.
TIPO_ARCHIVO_ESCRUTINIO = 1

IMPERSONATE = "chrome124"
TIMEOUT = 30
RETRIES = 4
DELAY_RANGE = (1.0, 2.5)  # segundos entre mesas, para no saturar el portal

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE_URL}/main/actas",
    "Accept-Language": "es-PE,es;q=0.9",
}


@dataclass
class ActaRecord:
    mesa: str
    tipo: str
    id_acta: str
    archivo_id: str
    archivo: str
    estado: str  # ok | omitido | sin_acta | sin_archivo | error_*


def _session():
    """Sesión HTTP con huella de Chrome (evita el WAF del portal)."""
    if not _HAS_CFFI:
        log.warning("curl_cffi no está instalado: el portal probablemente "
                    "devuelva HTML en vez de JSON. Instala: pip install curl_cffi")
    return cffi_requests.Session()


def _get(session, url: str, **kw):
    """GET con reintentos exponenciales e impersonate de Chrome."""
    last_exc = None
    for intento in range(1, RETRIES + 1):
        try:
            if _HAS_CFFI:
                return session.get(url, impersonate=IMPERSONATE,
                                   headers=HEADERS, timeout=TIMEOUT, **kw)
            return session.get(url, headers=HEADERS, timeout=TIMEOUT, **kw)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            espera = 2 ** intento
            log.warning("Fallo GET (%s/%s) %s -> %s; reintenta en %ss",
                        intento, RETRIES, url, exc, espera)
            time.sleep(espera)
    raise RuntimeError(f"GET agotó reintentos: {url}") from last_exc


def buscar_acta_mesa(session, mesa: str, id_eleccion: int) -> dict | None:
    """
    Paso 1: busca las actas de una mesa y devuelve la del tipo de elección
    pedido, solo si está Contabilizada (garantiza PDF final disponible).
    """
    r = _get(session, f"{BACKEND}/actas/buscar/mesa",
             params={"codigoMesa": mesa, "idEleccion": id_eleccion})
    if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
        return None
    actas = (r.json() or {}).get("data") or []
    for acta in actas:
        if acta.get("idEleccion") == id_eleccion and \
                acta.get("codigoEstadoActa") == "C":  # C = Contabilizada
            return acta
    return None


def obtener_archivo_escrutinio(session, id_acta) -> dict | None:
    """Paso 2: detalle del acta -> archivo tipo 1 (ACTA DE ESCRUTINIO)."""
    r = _get(session, f"{BACKEND}/actas/{id_acta}")
    if r.status_code != 200:
        return None
    data = (r.json() or {}).get("data") or {}
    for archivo in data.get("archivos") or []:
        if archivo.get("tipo") == TIPO_ARCHIVO_ESCRUTINIO:
            return archivo
    return None


def obtener_url_firmada(session, archivo_id: str) -> str | None:
    """Paso 3: canjea el id del archivo por la URL firmada de S3 (expira)."""
    r = _get(session, f"{BACKEND}/actas/file", params={"id": archivo_id})
    if r.status_code != 200:
        return None
    url = (r.json() or {}).get("data") or ""
    return url if url.startswith("https://") else None


def descargar_acta(session, mesa: str, tipo: str, out_dir: Path) -> ActaRecord:
    """Cadena completa para una mesa: buscar -> archivos -> signed URL -> PDF."""
    destino = out_dir / f"acta_{tipo}_{mesa}.pdf"
    if destino.exists():
        return ActaRecord(mesa, tipo, "", "", str(destino), "omitido")

    id_eleccion = TIPO_ELECCION[tipo]
    acta = buscar_acta_mesa(session, mesa, id_eleccion)
    if not acta:
        return ActaRecord(mesa, tipo, "", "", "", "sin_acta")

    archivo = obtener_archivo_escrutinio(session, acta["id"])
    if not archivo:
        return ActaRecord(mesa, tipo, str(acta["id"]), "", "", "sin_archivo")

    url = obtener_url_firmada(session, archivo["id"])
    if not url:
        return ActaRecord(mesa, tipo, str(acta["id"]), archivo["id"], "", "error_signed_url")

    try:
        # la URL firmada de S3 se descarga directo (sin headers de la SPA)
        r = session.get(url, impersonate=IMPERSONATE, timeout=60) if _HAS_CFFI \
            else session.get(url, timeout=60)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            destino.write_bytes(r.content)
            return ActaRecord(mesa, tipo, str(acta["id"]), archivo["id"],
                              str(destino), "ok")
        return ActaRecord(mesa, tipo, str(acta["id"]), archivo["id"], "",
                          f"error_status_{r.status_code}")
    except Exception as exc:  # noqa: BLE001
        return ActaRecord(mesa, tipo, str(acta["id"]), archivo["id"], "",
                          f"error_{type(exc).__name__}")


def correr(tipo: str, inicio: int, max_actas: int, out_dir: Path, manifest: Path):
    """
    Recorre mesas secuenciales desde `inicio` hasta juntar `max_actas` PDFs.
    Se recorren más mesas que actas pedidas porque algunas pueden no estar
    contabilizadas o no tener archivo.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    session = _session()
    registros: list[ActaRecord] = []
    descargadas = 0
    mesa_num = inicio
    limite_busqueda = inicio + max_actas * 10  # tope defensivo

    log.info("Descargando %s actas de escrutinio (tipo=%s) -> %s",
             max_actas, tipo, out_dir)
    while descargadas < max_actas and mesa_num < limite_busqueda:
        mesa = str(mesa_num).zfill(6)
        rec = descargar_acta(session, mesa, tipo, out_dir)
        registros.append(rec)
        if rec.estado in ("ok", "omitido"):
            descargadas += 1
        log.info("[%s/%s] mesa %s -> %s", descargadas, max_actas, mesa, rec.estado)
        mesa_num += 1
        time.sleep(random.uniform(*DELAY_RANGE))

    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["mesa", "tipo", "id_acta",
                                           "archivo_id", "archivo", "estado"])
        w.writeheader()
        for r in registros:
            w.writerow(asdict(r))
    ok = sum(1 for r in registros if r.estado in ("ok", "omitido"))
    log.info("Listo. %s/%s actas disponibles. Manifest: %s", ok, max_actas, manifest)


def main():
    p = argparse.ArgumentParser(description="Descarga actas de escrutinio ONPE EG2026 (1ª vuelta)")
    p.add_argument("--tipo", default="presidencial", choices=list(TIPO_ELECCION))
    p.add_argument("--inicio", type=int, default=1, help="Número de mesa inicial (secuencial)")
    p.add_argument("--max", type=int, default=10, help="Cantidad de actas a descargar")
    p.add_argument("--out", type=Path, default=Path("../../data/raw_pdf"))
    p.add_argument("--manifest", type=Path, default=Path("../../data/manifest.csv"))
    args = p.parse_args()
    correr(args.tipo, args.inicio, args.max, args.out, args.manifest)


if __name__ == "__main__":
    main()
