"""
Potencia y precisión de las muestras del estudio.

Responde con evidencia la pregunta "¿24 actas alcanzan para afirmar un
resultado?" (y la simétrica para las 76 manuscritas). La unidad de muestreo
es el ACTA, no el campo: los ~43 campos de un acta comparten escribano,
escáner y calidad, así que la inferencia debe agruparse por acta.

Qué calcula, para cada subconjunto:
  1. IC 95% por bootstrap agrupado por acta (remuestrea actas completas).
  2. IC 95% de Wilson ignorando el agrupamiento (referencia optimista).
  3. ICC (ANOVA de efectos aleatorios) y efecto de diseño DEFF = 1+(m-1)*ICC,
     con m = campos por acta; n_efectivo = n_campos / DEFF.
  4. Actas necesarias para alcanzar ±5, ±3 y ±2 pp con ese DEFF.
  5. IC de la diferencia STAE - manuscritas (bootstrap de dos muestras).

Hallazgo que sustenta el paper: en las STAE el parseo es determinista, la
varianza entre actas queda POR DEBAJO de la binomial (ICC ~ 0, DEFF ~ 1) y
24 actas bastan para ±0.6 pp; en las manuscritas la caligrafía introduce
DEFF ~ 3, y por eso 76 actas solo alcanzan ±2.9 pp.

Uso:
    python potencia_muestral.py --out ../../docs/resultados/potencia_muestral.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

SEED = 2026
B = 20000

# (etiqueta, archivo, clave_campos, clave_correctos)
FUENTES = [
    ("stae_nacidas_digitales",
     "evaluacion_stae_electronicas.json", "campos", "correctos"),
    ("manuscritas_v5_regla",
     "evaluacion_nacional_v5_regla.json", "campos_evaluados", "campos_correctos"),
]


def cargar(base: Path, archivo: str, k_campos: str, k_ok: str):
    d = json.loads((base / archivo).read_text(encoding="utf-8"))
    return [(a[k_campos], a[k_ok]) for a in d["actas"]]


def bootstrap_agrupado(actas, rng, b=B):
    """Remuestrea ACTAS completas con reemplazo; devuelve percentiles 2.5/97.5."""
    n = len(actas)
    reps = []
    for _ in range(b):
        s = [actas[rng.randrange(n)] for _ in range(n)]
        reps.append(sum(x[1] for x in s) / sum(x[0] for x in s))
    reps.sort()
    return reps[int(0.025 * b)], reps[int(0.975 * b)]


def wilson(k: int, n: int, z: float = 1.96):
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    semi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centro - semi, centro + semi


def icc_deff(actas):
    """ICC one-way y efecto de diseño. ICC se trunca en 0 (subdispersión)."""
    k = len(actas)
    m = sum(c for c, _ in actas) / k
    p = sum(x for _, x in actas) / sum(c for c, _ in actas)
    var_obs = sum(c * (x / c - p) ** 2 for c, x in actas) / (k - 1)
    var_bin = p * (1 - p)
    icc = max(0.0, (var_obs - var_bin) / (var_bin * (m - 1))) if m > 1 else 0.0
    return icc, m, 1 + (m - 1) * icc


def analizar(nombre, actas, rng):
    n_campos = sum(c for c, _ in actas)
    n_ok = sum(x for _, x in actas)
    p = n_ok / n_campos
    lo_b, hi_b = bootstrap_agrupado(actas, rng)
    lo_w, hi_w = wilson(n_ok, n_campos)
    icc, m, deff = icc_deff(actas)
    requeridas = {}
    for e in (0.05, 0.03, 0.02):
        campos = (1.96 ** 2) * p * (1 - p) / (e ** 2) * deff
        requeridas[f"+-{int(e*100)}pp"] = {
            "campos": round(campos), "actas": math.ceil(campos / m)}
    return {
        "n_actas": len(actas), "n_campos": n_campos, "n_correctos": n_ok,
        "exactitud": round(p, 4),
        "ic95_bootstrap_agrupado": [round(lo_b, 4), round(hi_b, 4)],
        "semiamplitud_pp": round(100 * (hi_b - lo_b) / 2, 2),
        "ic95_wilson_sin_agrupar": [round(lo_w, 4), round(hi_w, 4)],
        "icc": round(icc, 4), "campos_por_acta": round(m, 1),
        "deff": round(deff, 2), "n_efectivo_campos": round(n_campos / deff),
        "actas_requeridas": requeridas,
    }


def diferencia(a, b, rng, n=B):
    reps = []
    for _ in range(n):
        sa = [a[rng.randrange(len(a))] for _ in range(len(a))]
        sb = [b[rng.randrange(len(b))] for _ in range(len(b))]
        reps.append(sum(x[1] for x in sa) / sum(x[0] for x in sa)
                    - sum(x[1] for x in sb) / sum(x[0] for x in sb))
    reps.sort()
    return {
        "brecha_pp": round(100 * (sum(x[1] for x in a) / sum(x[0] for x in a)
                                  - sum(x[1] for x in b) / sum(x[0] for x in b)), 2),
        "ic95_pp": [round(100 * reps[int(0.025 * n)], 2),
                    round(100 * reps[int(0.975 * n)], 2)],
        "p_valor_bootstrap_h0_menor_igual_0": sum(1 for r in reps if r <= 0) / n,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--resultados", default="../../docs/resultados",
                    help="carpeta con las evaluaciones .json")
    ap.add_argument("--out", default="../../docs/resultados/potencia_muestral.json")
    args = ap.parse_args()

    base = Path(args.resultados)
    rng = random.Random(SEED)
    datos = {n: cargar(base, f, kc, ko) for n, f, kc, ko in FUENTES}

    salida = {"seed": SEED, "n_bootstrap": B, "unidad_de_agrupamiento": "acta",
              "subconjuntos": {}}
    for nombre, actas in datos.items():
        salida["subconjuntos"][nombre] = analizar(nombre, actas, rng)
    salida["contraste_stae_vs_manuscritas"] = diferencia(
        datos["stae_nacidas_digitales"], datos["manuscritas_v5_regla"], rng)

    Path(args.out).write_text(json.dumps(salida, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    for nombre, r in salida["subconjuntos"].items():
        print(f"{nombre}: {100*r['exactitud']:.2f}% "
              f"IC95 [{100*r['ic95_bootstrap_agrupado'][0]:.2f}, "
              f"{100*r['ic95_bootstrap_agrupado'][1]:.2f}] "
              f"(+-{r['semiamplitud_pp']} pp) | ICC={r['icc']} DEFF={r['deff']} "
              f"| n_efectivo={r['n_efectivo_campos']} campos")
    c = salida["contraste_stae_vs_manuscritas"]
    print(f"brecha = {c['brecha_pp']} pp  IC95 {c['ic95_pp']}  "
          f"p = {c['p_valor_bootstrap_h0_menor_igual_0']}")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
