"""
Análisis estadístico de la evaluación (validez científica del paper).

Reporta, a partir de un evaluacion.json (lista de actas con campos correctos /
evaluados), lo que un revisor exige:

    - Estimador puntual de la exactitud por campo.
    - Intervalo de confianza 95% por BOOTSTRAP AGRUPADO POR ACTA: se remuestrean
      ACTAS (no campos) con reemplazo, porque los ~43 campos de una misma acta
      comparten escribiente y calidad de escaneo → están correlacionados. Un IC
      binomial ingenuo sobre campos independientes subestimaría el error.
    - Distribución de la exactitud por acta (media, sd, min, max).
    - CER global y su IC 95% (mismo bootstrap agrupado).
    - Si se pasa --muestra, la cobertura geográfica (departamentos) como
      evidencia de representatividad de la muestra aleatoria.

Uso:
    python analisis_estadistico.py --eval ../../data/muestra_salida/evaluacion.json \
        --muestra ../../data/muestra/muestra.json --boot 10000
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st
from pathlib import Path


def bootstrap_ci(actas, valor_fn, peso_fn, n_boot=10000, seed=2026, alfa=0.05):
    """
    IC bootstrap agrupado: cada réplica remuestrea ACTAS con reemplazo y
    recalcula el estimador ponderado (suma de aciertos / suma de campos).
    valor_fn(acta) -> numerador; peso_fn(acta) -> denominador.
    """
    rng = random.Random(seed)
    m = len(actas)
    reps = []
    for _ in range(n_boot):
        muestra = [actas[rng.randrange(m)] for _ in range(m)]
        num = sum(valor_fn(a) for a in muestra)
        den = sum(peso_fn(a) for a in muestra)
        if den:
            reps.append(num / den)
    reps.sort()
    lo = reps[int((alfa / 2) * len(reps))]
    hi = reps[int((1 - alfa / 2) * len(reps))]
    return lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", type=Path, required=True)
    ap.add_argument("--muestra", type=Path, default=None)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    data = json.loads(args.eval.read_text(encoding="utf-8"))
    actas = data["actas"]
    n = len(actas)

    # exactitud por campo (ponderada) e IC bootstrap agrupado
    tot_ok = sum(a["campos_correctos"] for a in actas)
    tot_ca = sum(a["campos_evaluados"] for a in actas)
    exac = tot_ok / tot_ca
    ci_lo, ci_hi = bootstrap_ci(
        actas, lambda a: a["campos_correctos"], lambda a: a["campos_evaluados"],
        n_boot=args.boot)

    # distribución por acta
    por_acta = [a["campos_correctos"] / a["campos_evaluados"]
                for a in actas if a["campos_evaluados"]]

    # CER global (promedio simple por acta) e IC
    cer_prom = st.mean(a["cer_promedio"] for a in actas)
    ci_cer_lo, ci_cer_hi = bootstrap_ci(
        actas, lambda a: a["cer_promedio"], lambda a: 1.0, n_boot=args.boot)

    print("=" * 64)
    print(f"ACTAS EVALUADAS: {n}   CAMPOS: {tot_ca}")
    print("-" * 64)
    print(f"Exactitud por campo: {exac*100:.2f}%  "
          f"IC95% [{ci_lo*100:.2f}, {ci_hi*100:.2f}]  "
          f"(±{(ci_hi-ci_lo)/2*100:.2f} pp)")
    print(f"CER global:          {cer_prom:.4f}  "
          f"IC95% [{ci_cer_lo:.4f}, {ci_cer_hi:.4f}]")
    print("-" * 64)
    print(f"Exactitud por acta:  media={st.mean(por_acta)*100:.1f}%  "
          f"sd={st.pstdev(por_acta)*100:.1f}pp  "
          f"min={min(por_acta)*100:.0f}%  max={max(por_acta)*100:.0f}%")
    print(f"Actas perfectas:     {sum(1 for a in actas if a.get('acta_perfecta'))}/{n}")

    resultado = {
        "n_actas": n, "n_campos": tot_ca,
        "exactitud_campo": round(exac, 4),
        "ic95_exactitud": [round(ci_lo, 4), round(ci_hi, 4)],
        "margen_error_pp": round((ci_hi - ci_lo) / 2 * 100, 2),
        "cer_global": round(cer_prom, 4),
        "ic95_cer": [round(ci_cer_lo, 4), round(ci_cer_hi, 4)],
        "exactitud_por_acta": {
            "media": round(st.mean(por_acta), 4),
            "sd": round(st.pstdev(por_acta), 4),
            "min": round(min(por_acta), 4),
            "max": round(max(por_acta), 4),
        },
        "actas_perfectas": sum(1 for a in actas if a.get("acta_perfecta")),
        "n_bootstrap": args.boot,
    }

    if args.muestra and args.muestra.exists():
        m = json.loads(args.muestra.read_text(encoding="utf-8"))
        print("-" * 64)
        print(f"Cobertura: {m.get('departamentos_ubigeo_cubiertos')} departamentos "
              f"(ubigeo) | tasa de acierto muestreo={m.get('tasa_acierto')}")
        resultado["cobertura_departamentos"] = m.get("departamentos_ubigeo_cubiertos")
        resultado["distribucion_departamental"] = m.get("distribucion_departamental")
        resultado["seed_muestra"] = m.get("seed")
    print("=" * 64)

    if args.out:
        args.out.write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print("Guardado:", args.out)


if __name__ == "__main__":
    main()
