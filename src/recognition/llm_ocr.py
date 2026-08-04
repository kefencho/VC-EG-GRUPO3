"""
Reconocimiento del acta COMPLETA con un LLM multimodal (Gemini), en modo
FEW-SHOT — el experimento que sugirió la profesora.

Idea (distinta al pipeline): en vez de detección por plantilla + OCR celda a
celda, se le da al LLM la imagen del acta ENTERA junto con unos pocos ejemplos
resueltos (imagen + su JSON de votos oficiales) y se le pide leer una acta
nueva y devolver el mismo JSON. Es end-to-end: el modelo localiza y lee.

Se evalúa igual que el pipeline: exactitud por campo y CER contra el ground
truth oficial de la API ONPE, sobre las MISMAS actas manuscritas → comparación
directa LLM few-shot vs. plantilla+EasyOCR.

Usa Gemini (gratuito, free tier) vía REST, sin dependencias extra. La API key
se lee de onpe_actas/.env (GEMINI_API_KEY), nunca se imprime ni se versiona.

Uso:
    python llm_ocr.py --n 15 --shots 2 --out ../../data/muestra/salida_llm
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.piloto_10_actas import evaluar_acta, N_PARTIDOS  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


def cargar_env():
    env = RAIZ / ".env"
    if env.exists():
        for ln in env.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def img_b64(png_path: Path, alto: int = 1600, calidad: int = 80) -> str:
    """Reduce el acta a `alto` px y la codifica JPEG base64 (liviano para el LLM)."""
    img = cv2.imdecode(np.frombuffer(png_path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    if h > alto:
        img = cv2.resize(img, (int(w * alto / h), alto), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, calidad])
    return base64.b64encode(buf.tobytes()).decode()


def gt_a_json_esperado(gt: dict) -> dict:
    """Construye el JSON 'correcto' que el LLM debería devolver, desde el GT oficial."""
    partidos = {pos: (0 if v is None else v)
                for pos, v in (gt.get("votos_partido") or {}).items()}
    return {
        "mesa": gt["mesa"],
        "votos_partido": partidos,
        "votos_blancos": gt.get("votos_blancos"),
        "votos_nulos": gt.get("votos_nulos"),
        "votos_impugnados": gt.get("votos_impugnados"),
        "total_emitidos": gt.get("total_emitidos"),
        "total_electores": gt.get("total_electores"),
    }


INSTRUCCION = (
    "Eres un sistema de digitación de actas electorales de la ONPE (Perú 2026). "
    "Recibes la imagen de un ACTA DE ESCRUTINIO presidencial. Lee los números "
    "MANUSCRITOS de la columna 'TOTAL DE VOTOS': hay 38 filas de organizaciones "
    "políticas (posiciones 01 a 38; las filas vacías del formulario valen 0), y "
    "abajo VOTOS EN BLANCO, VOTOS NULOS, VOTOS IMPUGNADOS y TOTAL DE VOTOS "
    "EMITIDOS. Lee también el número de mesa y el total de electores hábiles. "
    "Devuelve SOLO un JSON válido con esta forma exacta:\n"
    '{"mesa":"NNNNNN","votos_partido":{"01":n,...,"38":n},'
    '"votos_blancos":n,"votos_nulos":n,"votos_impugnados":n,'
    '"total_emitidos":n,"total_electores":n}\n'
    "Cada valor es un entero. Una celda en blanco es 0. No expliques nada."
)


def construir_partes(shots, target_b64):
    """Arma el contenido multimodal: instrucción + ejemplos (img+json) + target."""
    partes = [{"text": INSTRUCCION}]
    for ej_b64, ej_json in shots:
        partes.append({"text": "\nEJEMPLO — imagen del acta:"})
        partes.append({"inline_data": {"mime_type": "image/jpeg", "data": ej_b64}})
        partes.append({"text": "Respuesta correcta:\n" +
                       json.dumps(ej_json, ensure_ascii=False)})
    partes.append({"text": "\nAHORA lee esta acta y responde SOLO el JSON:"})
    partes.append({"inline_data": {"mime_type": "image/jpeg", "data": target_b64}})
    return partes


def llamar_gemini(partes, modelo, reintentos=6) -> dict | None:
    key = os.environ["GEMINI_API_KEY"]
    url = f"{ENDPOINT}/{modelo}:generateContent"
    print("Modelo:", modelo)
    print("URL:", url)
    payload = {
        "contents": [{"parts": partes}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    data = json.dumps(payload).encode("utf-8")
    for intento in range(1, reintentos + 1):
        try:
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={"Content-Type": "application/json", "x-goog-api-key": key})
            with urllib.request.urlopen(req, timeout=90) as r:
                resp = json.loads(r.read().decode("utf-8"))
            txt = resp["candidates"][0]["content"]["parts"][0]["text"]
            m = re.search(r"\{.*\}", txt, re.DOTALL)
            return json.loads(m.group(0)) if m else None
        except urllib.error.HTTPError as e:
            print("\n========================")
            print("HTTP:", e.code)

            try:
                body = e.read().decode("utf-8")
                print(body)
            except Exception:
                pass

            print("========================\n")
            # 429 (cuota) y 503 (modelo saturado) son transitorios → backoff largo
            espera = 6 * intento if e.code in (429, 503) else 2 * intento
            if intento < reintentos:
                time.sleep(espera)
            else:
                print(f"  HTTP {e.code} tras {reintentos} intentos", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            if intento < reintentos:
                time.sleep(2 * intento)
            else:
                print(f"  error: {e}", file=sys.stderr)
    return None


def normalizar(pred_llm: dict) -> dict:
    """Adapta la respuesta del LLM al formato que espera evaluar_acta()."""
    vp = {f"{int(k):02d}": v for k, v in (pred_llm.get("votos_partido") or {}).items()}
    return {
        "votos_partido": vp,
        "votos_blancos": pred_llm.get("votos_blancos"),
        "votos_nulos": pred_llm.get("votos_nulos"),
        "votos_impugnados": pred_llm.get("votos_impugnados"),
        "total_emitidos": pred_llm.get("total_emitidos"),
        "total_electores": pred_llm.get("total_electores"),
        "mesa_ocr": int(pred_llm["mesa"]) if str(pred_llm.get("mesa", "")).isdigit() else None,
        "total_ciudadanos_que_votaron": pred_llm.get("total_emitidos"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procesadas", type=Path, default=RAIZ / "data" / "muestra" / "processed")
    ap.add_argument("--gt", type=Path, default=RAIZ / "data" / "muestra" / "ground_truth")
    ap.add_argument("--tipos", type=Path, default=RAIZ / "data" / "muestra" / "tipos.json")
    ap.add_argument("--n", type=int, default=15, help="actas de prueba")
    ap.add_argument("--shots", type=int, default=2, help="ejemplos few-shot")
    ap.add_argument("--out", type=Path, default=RAIZ / "data" / "muestra" / "salida_llm")
    args = ap.parse_args()

    cargar_env()
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Falta GEMINI_API_KEY en onpe_actas/.env")
    modelo = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    args.out.mkdir(parents=True, exist_ok=True)

    # solo actas manuscritas (las electrónicas se parsean por texto, no aplican)
    manus = set(json.loads(args.tipos.read_text(encoding="utf-8"))["manuscritas"])
    # OJO: NO filtrar por "_p" en el stem — "acta_presidencial" ya lo contiene;
    # las electrónicas multipágina terminan en _p0/_p1 (regex de sufijo).
    disponibles = sorted(
        p for p in args.procesadas.glob("acta_presidencial_*.png")
        if not re.search(r"_p\d+$", p.stem) and p.stem.split("_")[-1] in manus
        and (args.gt / f"{p.stem.split('_')[-1]}.json").exists())

    shots_paths = disponibles[:args.shots]
    test_paths = disponibles[args.shots:args.shots + args.n]

    shots = []
    for p in shots_paths:
        mesa = p.stem.split("_")[-1]
        gt = json.loads((args.gt / f"{mesa}.json").read_text(encoding="utf-8"))
        shots.append((img_b64(p), gt_a_json_esperado(gt)))
    print(f"Modelo {modelo} | {len(shots)} ejemplos few-shot | {len(test_paths)} actas de prueba")

    actas_eval = []
    tot_c = tot_ok = 0
    cers = []
    for i, p in enumerate(test_paths, 1):
        mesa = p.stem.split("_")[-1]
        pred_llm = llamar_gemini(construir_partes(shots, img_b64(p)), modelo)
        if not pred_llm:
            print(f"[{i}/{len(test_paths)}] mesa {mesa}: sin respuesta")
            continue
        pred = normalizar(pred_llm)
        (args.out / f"{mesa}.json").write_text(
            json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8")
        gt = json.loads((args.gt / f"{mesa}.json").read_text(encoding="utf-8"))
        ev = evaluar_acta(pred, gt)
        ev["mesa"] = mesa
        actas_eval.append(ev)
        tot_c += ev["campos_evaluados"]
        tot_ok += ev["campos_correctos"]
        cers.append(ev["cer_promedio"])
        print(f"[{i}/{len(test_paths)}] mesa {mesa}: {ev['campos_correctos']}/{ev['campos_evaluados']} "
              f"({100*ev['exactitud_campo']:.0f}%) CER={ev['cer_promedio']}")
        time.sleep(1.0)  # cortesía con el rate limit del free tier

    n = len(actas_eval)
    resumen = {"actas": actas_eval, "totales": {
        "modelo": modelo, "shots": len(shots), "actas_evaluadas": n,
        "exactitud_campo_global": round(tot_ok / tot_c, 4) if tot_c else 0,
        "campos_evaluados": tot_c, "campos_correctos": tot_ok,
        "cer_promedio_global": round(sum(cers) / n, 4) if n else 0,
        "actas_perfectas": sum(1 for a in actas_eval if a["acta_perfecta"]),
    }}
    (args.out / "evaluacion.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    t = resumen["totales"]
    print("=" * 60)
    print(f"LLM {modelo} few-shot: {t['campos_correctos']}/{t['campos_evaluados']} "
          f"campos ({100*t['exactitud_campo_global']:.2f}%) | CER={t['cer_promedio_global']} "
          f"| actas perfectas {t['actas_perfectas']}/{n}")


if __name__ == "__main__":
    main()
