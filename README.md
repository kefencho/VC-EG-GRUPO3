# onpe_actas — Detección y Reconocimiento Automático de Resultados Electorales en Actas de Escrutinio (ONPE 2026 – 1ª Vuelta)

**Maestría en Inteligencia Artificial · Visión por Computadora · Grupo 3 · Sección B · 2026‑1**

Sistema de Visión por Computadora que **detecta las regiones de interés** de las
actas de escrutinio de la ONPE y **reconoce los valores numéricos** (totales,
votos por organización política, votos en blanco/nulos/impugnados), para
transformar la información visual en **datos estructurados (JSON)** listos para
análisis y auditoría.

> 🗳️ **Resumen visual del proyecto** (pipeline, resultados con IC 95%,
> hallazgos y entregables):
> **https://carlosperez100.github.io/onpe_actas/resumen.html**
>
> 🖼️ **Póster en el navegador** (réplica web del A0, en inglés):
> **https://carlosperez100.github.io/onpe_actas/poster.html**
>
> ▶️ **Correrlo tú mismo sin asistente:** doble clic en `EJECUTAR - EASYOCR.bat`
> (guía completa en [docs/COMO_CORRERLO.md](docs/COMO_CORRERLO.md)) ·
> 📊 Evaluación nacional en [docs/EVALUACION_NACIONAL.md](docs/EVALUACION_NACIONAL.md)

---

## Entregables del trabajo final

| Entregable | Dónde está | Cómo se regenera |
|---|---|---|
| **Paper** (inglés, formato WVC/IEEE, 5 págs, abstract 148 palabras) | [paper/main.pdf](paper/main.pdf) · versión en español: [paper/main_es.pdf](paper/main_es.pdf) | `cd paper && pdflatex main.tex` (dos pasadas) |
| **Póster** (inglés, A0 vertical, una página) | PDF: [poster/poster.pdf](poster/poster.pdf) · web: **[carlosperez100.github.io/onpe_actas/poster.html](https://carlosperez100.github.io/onpe_actas/poster.html)** | `cd poster && pdflatex poster.tex` (dos pasadas); la versión web es [docs/poster.html](docs/poster.html) |
| **Presentación** (español, 15 min, con notas del expositor) | genera `Presentacion - Grupo 3.pptx` | `cd presentacion && npm install && node generar_diapositivas.js` (acepta una ruta de salida como argumento) |
| **Implementación** | este repositorio | ver *Reproducir los resultados del paper* |

El paper también se abre en **Overleaf gratis con un clic**:
[abrir proyecto](https://www.overleaf.com/docs?snip_uri=https://raw.githubusercontent.com/carlosperez100/onpe_actas/main/paper/overleaf.zip)
(para la versión en español: Menu → Settings → Main document → `main_es.tex`).

---

## Integrantes

- Josemanuel Rossy Cañari Palante — jose.canari@outlook.com.pe
- Kenny Asto Hinostroza — kenny.asto.hinostroza@gmail.com
- Melissa Dessire Aylas Barranca — melissa.aylas@gmail.com
- Carlos Pérez Pérez

---

## 1. Problema

Las actas de escrutinio son la fuente oficial de los resultados por mesa, pero
se publican en **formato visual** (PDF/imagen), lo que impide su procesamiento
automático a gran escala. La extracción manual es lenta, propensa a errores de
digitación y difícil de auditar. Además, las imágenes presentan ruido, baja
resolución, inclinación, sellos y firmas que complican el reconocimiento.

## 2. Objetivo

Desarrollar un sistema basado en Visión por Computadora capaz de **detectar y
reconocer automáticamente** los resultados electorales de las actas de las
Elecciones Generales del Perú 2026.

**Objetivos específicos**

1. Construir un dataset de actas obtenidas del portal oficial de la ONPE.
2. Detectar las regiones de interés. **Implementado** con plantilla de layout
   fijo registrada sobre las marcas fiduciales del formulario .
3. Reconocer los valores numéricos registrados (OCR de dígitos manuscritos).
4. Transformar la información en datos estructurados (JSON).
5. Evaluar el sistema con métricas de reconocimiento (exactitud por campo y
   CER) contra el ground truth oficial, con intervalos de confianza.

## 3. Dataset

**Actas de Escrutinio – Elecciones Generales del Perú 2026 (1ª Vuelta).**

- **Fuente:** Portal de Resultados Electorales de la ONPE (actas oficiales en
  PDF/imagen).
- **Recolección:** descarga automatizada con el scraper de este repo
  (`src/scraper/download_actas.py`).
- **Contenido aprovechable:** número de mesa, resultados por organización
  política, votos blancos/nulos/impugnados, total de votos emitidos, total de
  ciudadanos que votaron, firmas de miembros de mesa.

### Relevancia para la tarea
Las actas tienen regiones claramente delimitadas (tabla de resultados, totales,
firmas, observaciones) ideales para **detección**, y campos manuscritos
(números y totales) que requieren **reconocimiento**. Aplicación real:
automatización del procesamiento documental electoral y apoyo a auditorías.

### Limitaciones y desafíos
- **Calidad de imagen:** resoluciones distintas, inclinación, contraste variable.
- **Escritura manuscrita:** estilos diversos, trazos poco legibles, números
  parciales.
- **Ruido visual:** sellos sobre los campos, firmas cercanas, marcas de impresión.
- **Desbalance:** partidos con pocos votos, predominio de valores pequeños.
- **Etiquetado:** el dataset no trae anotaciones de detección. Las cajas se
  autogeneran con la plantilla registrada; los valores de cada campo sí vienen
  gratis de la API oficial (ver *ground truth* sin anotación manual).
- **Complejidad documental:** múltiples formatos (presidencial vs. congresal).

## 4. Enfoque / Pipeline

```
1. ENTRADA            Acta digitalizada (PDF → imagen, 300 dpi)
2. PREPROCESAMIENTO   Deskew · CLAHE · denoise · binarización por celda (Otsu)
3. DETECCIÓN          Plantilla de 46 regiones registrada sobre las marcas
                      fiduciales (RANSAC de traslación + afín parcial)
4. RECONOCIMIENTO     EasyOCR restringido a dígitos sobre cada celda limpiada
5. SALIDA             Datos estructurados (JSON) por acta + evaluación
```

### Métricas de evaluación

Lo que **se reporta** en el paper, el póster y los informes:

- **Exactitud por campo:** coincidencia exacta contra el valor oficial digitado.
- **CER:** tasa de error de caracteres sobre la cadena de dígitos.
- **Intervalos:** bootstrap agrupado por acta (10,000 réplicas); el acta es la
  unidad de muestreo, no el campo.

Métricas de **detección** (mAP, Precision, Recall con Ultralytics `val`) y WER
quedan para la ruta con detector aprendido: hoy la localización se resuelve por
plantilla registrada y no hay modelo entrenado que evaluar.

## 5. Motivación, supuestos, riesgos y restricciones

- **Motivación:** aplicar VC moderna a un problema documental real con impacto
  social (transparencia electoral).
- **Supuestos:** actas representativas, calidad suficiente, valores legibles.
- **Riesgos:** calidad insuficiente, errores en manuscrito, necesidad de muchas
  anotaciones, límites de hardware.
- **Restricciones:** tiempo de entrenamiento, recursos computacionales,
  disponibilidad parcial del dataset durante el proyecto.

---

## Estructura del repositorio

```
onpe_actas/
├── EJECUTAR.bat                  # corre el pipeline completo con doble clic
├── data/                         # dataset (no versionado; se regenera)
│   ├── raw_pdf/  raw_img/  processed/  annotations/
├── src/
│   ├── scraper/                  # descarga de actas + PDF→imagen + muestreo
│   ├── preprocessing/            # deskew, CLAHE, denoise, binarización
│   ├── detection/                # plantilla + registro fiducial
│   ├── recognition/              # OCR de dígitos + línea base con LLM
│   ├── pipeline/                 # orquestación, evaluación y estadística
│   └── utils/                    # métricas (CER, exactitud por campo)
├── docs/                         # informes, resumen y póster web
│   ├── resultados/               # evidencia JSON versionada de cada corrida
│   ├── figuras/                  # figuras de los informes y del póster web
│   ├── resumen.html              # resumen del proyecto (GitHub Pages)
│   └── poster.html               # réplica web del póster A0
├── paper/                        # fuentes LaTeX y PDF del paper (EN y ES)
├── poster/                       # fuente LaTeX y PDF del póster A0
├── presentacion/                 # generador del PPTX de la exposición
├── requirements.txt
└── README.md
```

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**GPU (opcional, OCR ~5× más rápido).** `easyocr` instala PyTorch en versión CPU.
Para usar GPU, instalar antes el build CUDA correspondiente a tu driver, p. ej.:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu126
```

`src/recognition/ocr.py` detecta la GPU automáticamente (medido: 57 → 10.8 s/acta
en una GTX 1650, misma exactitud). Con GPU conviene **un solo proceso** (sin
`--slice`). En Windows, si conviven `torch` y `cv2`, exportar
`KMP_DUPLICATE_LIB_OK=TRUE`.

---

## Reproducir los resultados del paper

Esta es la ruta **evaluada** (plantilla registrada por fiduciales + OCR de
dígitos), la que produjo el 59.58% del paper.

**Windows — un solo paso:** doble clic en `EJECUTAR.bat` (o `EJECUTAR.bat 100`
para replicar la muestra nacional completa). Guía detallada:
[docs/COMO_CORRERLO.md](docs/COMO_CORRERLO.md).

**Etapa por etapa** (multiplataforma). Cada script se corre **desde su propia
carpeta con rutas relativas**: OpenCV en Windows no abre rutas con tildes.

```bash
# 0) muestra aleatoria nacional reproducible (semilla publicada) + descarga + ground truth
cd src/scraper       && python muestreo_nacional.py --n 100 --seed 2026 --out ../../data/muestra
                        python pdf_to_images.py --in ../../data/muestra/raw_pdf --out ../../data/muestra/raw_img --dpi 300
# 1) preprocesamiento (deskew + CLAHE + denoise)
cd ../preprocessing  && python preprocess.py --in ../../data/muestra/raw_img --out ../../data/muestra/processed
# 2) detección de regiones por plantilla registrada en marcas fiduciales
cd ../detection      && python regiones_plantilla.py --in ../../data/muestra/processed --out ../../data/muestra/crops
# 3) reconocimiento (EasyOCR restringido a dígitos) -> JSON por acta
cd ../pipeline       && python piloto_10_actas.py --modo limpio --crops ../../data/muestra/crops \
                            --gt ../../data/muestra/ground_truth --out ../../data/muestra/salida
# 4) evaluación por campo y CER contra el ground truth oficial (regla vacío=0)
                        python evaluar_salidas.py --salidas ../../data/muestra/salida \
                            --gt ../../data/muestra/ground_truth --regla-cero --out ../../data/muestra/evaluacion.json
# 5) IC 95% por bootstrap agrupado por acta (10,000 réplicas)
                        python analisis_estadistico.py --eval ../../data/muestra/evaluacion.json \
                            --muestra ../../data/muestra/muestra.json --out ../../data/muestra/analisis.json
```

**Actas electrónicas (STAE), sin OCR** — el 24% de la muestra:

```bash
cd src/scraper && python extraer_electronicas.py --tipos ../../data/muestra/tipos.json \
    --pdf ../../data/muestra/raw_pdf --gt ../../data/muestra/ground_truth \
    --out ../../data/muestra/electronicas.json
```

**Comparación contra un LLM multimodal (few-shot)** — requiere `.env` con
`GEMINI_API_KEY` (capa gratuita; el archivo **no** se versiona):

```bash
cd src/recognition && python llm_ocr.py --n 15 --shots 2 --out ../../data/muestra/salida_llm
```

### Resultados esperados y evidencia versionada

| Corrida | Resultado | Evidencia en el repo |
|---|---|---|
| Nacional, plantilla registrada + regla vacío=0 | **59.58%** exactitud por campo, IC 95% [56.61, 62.48], CER 0.401 | `docs/resultados/analisis_nacional_v5.json` |
| Nacional, ablaciones (plantilla fija / OCR crudo) | 26.81% · 38.00% · 50.86% | `docs/resultados/evaluacion_nacional_*.json` |
| Piloto 10 actas, ablación v1→v4 | 43.95% → 58.37% | `docs/resultados/evaluacion_v[1-4]_*.json` |
| Actas electrónicas STAE (sin visión) | 95.12% (955/1,004 campos) | `docs/resultados/evaluacion_stae_electronicas.json` |
| Pipeline vs LLM few-shot (mismas 15 actas) | 60.93% vs 48.37% | `docs/resultados/evaluacion_llm_gemini.json` |

Las métricas se pueden **re-calcular sin volver a correr el OCR** con
`src/pipeline/evaluar_salidas.py` sobre las salidas ya guardadas.
Informes: [docs/EVALUACION_NACIONAL.md](docs/EVALUACION_NACIONAL.md),
[docs/PILOTO_VIABILIDAD.md](docs/PILOTO_VIABILIDAD.md),
[docs/EXPERIMENTO_LLM.md](docs/EXPERIMENTO_LLM.md).

---
## Nota legal y de datos

Las actas son documentos públicos publicados por la ONPE. Este proyecto es
**académico**; el dataset se reconstruye localmente con el scraper y no se
versiona en el repositorio. Si los endpoints de la ONPE cambian, ajusta
`src/scraper/download_actas.py`.
