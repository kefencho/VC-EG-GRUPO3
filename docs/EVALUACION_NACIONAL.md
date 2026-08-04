# Evaluación Nacional — Muestra aleatoria de 100 actas (EG2026, 1ª vuelta)

> Continuación del piloto de viabilidad (`PILOTO_VIABILIDAD.md`), ahora con
> **validez estadística**: muestra aleatoria nacional, intervalos de confianza
> por bootstrap agrupado e identificación de los modos de falla reales.
> Ejecutada: 04/05-jul-2026. Es la sección *Experiments* del paper WVC.

## 1. Diseño muestral (reproducible)

- **Universo:** ~88,064 mesas de sufragio (código máximo hallado por búsqueda
  binaria contra el portal ONPE).
- **Muestreo aleatorio simple sin reemplazo, semilla publicada = 2026**
  (`src/scraper/muestreo_nacional.py`); cualquiera regenera la misma muestra.
- **N = 100 actas**, tasa de acierto 100/100 códigos probados, **23
  departamentos** cubiertos (distribución proporcional al padrón: Lima
  concentra 36, coherente con ~1/3 del electorado).
- **100% con ground truth oficial** (votos digitados por la ONPE, vía API).
- Manifiesto completo: `data/muestra/muestra.json` (mesas, ubigeos, estado).

Esto corrige el sesgo del piloto (10 mesas secuenciales de Chachapoyas, un
solo centro de cómputo).

## 2. Hallazgo 1 — La población de actas es heterogénea

| Tipo | N | Naturaleza | Cómo se procesa |
|---|---:|---|---|
| **Manuscritas** | 76 (76%) | Escaneo físico, dígitos a lapicero, capa de texto vacía | Visión: detección + OCR |
| **Electrónicas (STAE)** | 24 (24%) | PDF nacido digital, firmado, votos impresos, 2 páginas | Parseo de capa de texto, sin OCR |

Las electrónicas se extraen con `src/scraper/extraer_electronicas.py`:
**95.12% de exactitud (955/1,004 campos)** emparejando por nombre de partido —
el residuo es del emparejamiento textual, no de lectura. Implicación de
ingeniería: el pipeline final debe **detectar el tipo de acta y enrutar**
(texto → parseo directo; escaneo → visión).

## 3. Hallazgo 2 — El encuadre del escaneo rompe la plantilla fija (y su solución)

En la muestra nacional aparecieron escaneos con **bandas negras de escáner y
desplazamientos de encuadre** (p. ej. mesa 084786, Ucayali: contenido corrido
~184 px). La plantilla de fracciones fijas leía la fila del vecino (CER > 1).

**Solución (v5): registro por marcas fiduciales.** El formulario imprime
cuadrados negros de registro en el borde. Se detectan (componentes conexos +
filtros de forma y posición), se emparejan con las 15 posiciones de referencia
mediante **RANSAC de traslación** (robusto a marcas faltantes y a falsos
positivos) y una **transformación afín parcial** lleva cada acta al marco de
referencia antes de recortar (`regiones_plantilla.py::alinear_por_fiduciales`).

## 4. Resultados (76 actas manuscritas, 3,268 campos, vs. oficial ONPE)

| Configuración | Exactitud por campo | CER |
|---|---:|---:|
| Sin registro, OCR puro | 26.81% | 0.724 |
| Sin registro + regla "vacío=0" | 50.86% (±3.06) | 0.482 |
| **Con registro (v5), OCR puro** | 38.00% | 0.617 |
| **Con registro (v5) + regla "vacío=0"** | **59.58%** | **0.401** |

**Resultado principal (para el abstract):**

> Exactitud por campo **59.58%, IC95% [56.61, 62.48] (±2.94 pp)**;
> CER **0.401, IC95% [0.360, 0.444]**. IC por bootstrap agrupado por acta
> (10,000 réplicas; el acta es el clúster: sus ~43 campos comparten
> escribiente y calidad de escaneo).

Distribución por acta: media 59.6%, sd 13.0 pp, rango 30%–84%. El registro
eliminó la cola colapsada (mínimo sube de 14% a 30%): la varianza residual es
**calidad de escritura y digitalización**, ya no alineación.

Comparación con el piloto sesgado (Chachapoyas, 10 actas): 58.4% — casualmente
similar al 59.6% nacional, pero ahora el número tiene margen de error válido y
cobertura nacional.

## 5. Lecciones para el paper

1. **La regla de dominio "celda vacía = 0" vale +21.6 pp** (38.0→59.6): los
   miembros de mesa dejan en blanco las celdas de partidos sin votos. Es
   semántica del formulario, no visión — y separarla evita atribuirle al OCR
   méritos que no tiene.
2. **El registro por fiduciales vale +8.7 pp** y es prerrequisito de cualquier
   método de plantilla sobre escaneos reales.
3. **El techo del OCR genérico en manuscrito peruano real es ~60%** con IC
   estrecho — la evidencia cuantitativa que justifica el fine-tuning de un
   reconocedor (TrOCR/DTrOCR) como siguiente paso. El dataset de entrenamiento
   sale gratis: cada acta descargada aporta ~43 pares (recorte, valor oficial).
4. **24% del problema no es visión** (actas STAE): reportarlo evita
   sobre-dimensionar el problema y da la recomendación de arquitectura
   (clasificar tipo → enrutar).

## 6. Detalles de implementación (tiempos, recursos y sistema)

### Tiempos por etapa — corrida nacional N=100 (medidos, 04/05-jul-2026)

| # | Etapa | Duración | Volumen |
|---|---|---:|---|
| 1 | Muestreo aleatorio + descarga (PDF + oficial) | 5.1 min | 100 PDFs (242 MB) + 100 JSON GT |
| 2 | Conversión PDF → PNG (300 DPI) | ~4 min | 124 imágenes (2.71 GB) |
| 3 | Preprocesamiento (deskew + CLAHE + denoise) | ~10 min | 124 imágenes (1.04 GB) |
| 4 | Recorte por plantilla registrada (fiduciales) | 0.7 min | 3,496 recortes (269 MB) |
| 5 | OCR (EasyOCR, 4 procesos, 76 actas manuscritas) | 116 min | 3,268 campos |
| 6 | Evaluación vs. oficial + regla de dominio | <1 min | 76 actas |
| 7 | Bootstrap IC 95% (10,000 réplicas) | <1 min | — |
| | **Total de cómputo** | **≈ 2 h 18 min** | |

El OCR concentra el 84% del tiempo (~1.5 min/acta efectivo con 4 procesos).

### Recursos

- **Red:** ~242 MB (actas) + <1 MB (API) + ~100 MB modelos EasyOCR (solo 1ª vez).
- **Disco:** ~4.3 GB de intermedios (regenerables; excluidos del repo).
- **Anotación manual:** 0 horas (verdad de terreno de la API oficial).
- **Costo monetario:** 0 (software libre y datos públicos).

### Sistema

| Componente | Característica |
|---|---|
| Equipo | HP Victus 16-d0xxx (laptop) |
| CPU | Intel Core i5-11400H (11ª gen), 6 núcleos / 12 hilos @ 2.70 GHz |
| RAM | 16 GB |
| GPU | NVIDIA GeForce GTX 1650 4 GB (evaluación reportada: **solo CPU**, torch 2.12.1+cpu) |
| SO | Windows 11 Home (build 26200) |
| Software | Python 3.13.9 · PyTorch 2.12.1 · OpenCV 5.0.0 · EasyOCR 1.7.2 · NumPy 2.3.5 · PyMuPDF · curl_cffi |

**Actualización GPU (06-jul-2026):** se habilitó CUDA (torch 2.12.1+cu126) y
`ocr.py` detecta la GPU automáticamente. Benchmark controlado (mismas 2 actas,
mismos recortes, misma exactitud 29/86 en ambos):

| Motor | Tiempo (2 actas) | Por acta | Speedup |
|---|---:|---:|---:|
| CPU (i5-11400H, 1 proceso) | 114.1 s | 57.1 s | 1× |
| **GPU (GTX 1650)** | **21.6 s** | **10.8 s** | **5.3×** |

Proyección: el OCR de la muestra nacional (116 min en 4 procesos CPU) baja a
~15-20 min en GPU con UN solo proceso; la corrida completa de 100 actas pasa
de ~2 h 18 min a ~45 min. La exactitud no cambia (mismo modelo, misma
aritmética; solo cambia dónde se ejecuta).

## 7. Reproducción

```bash
cd src/scraper    && python muestreo_nacional.py --n 100 --seed 2026 --out ../../data/muestra
cd src/scraper    && python pdf_to_images.py --in ../../data/muestra/raw_pdf --out ../../data/muestra/raw_img
cd src/preprocessing && python preprocess.py --in ../../data/muestra/raw_img --out ../../data/muestra/processed
cd src/detection  && python regiones_plantilla.py --in ../../data/muestra/processed --out ../../data/muestra/crops_v5
cd src/pipeline   && python piloto_10_actas.py --modo limpio --crops ../../data/muestra/crops_v5 \
                        --gt ../../data/muestra/ground_truth --out ../../data/muestra/salida_v5
cd src/pipeline   && python evaluar_salidas.py --salidas ../../data/muestra/salida_v5 \
                        --gt ../../data/muestra/ground_truth --regla-cero
cd src/pipeline   && python analisis_estadistico.py --eval ../../docs/resultados/evaluacion_nacional_v5_regla.json \
                        --muestra ../../data/muestra/muestra.json
cd src/scraper    && python extraer_electronicas.py   # actas STAE por capa de texto
```

Evidencia versionada: `docs/resultados/evaluacion_nacional_*.json`,
`docs/resultados/analisis_nacional*.json`.
