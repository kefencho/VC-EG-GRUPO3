# Cómo correr el pipeline TÚ MISMO (sin asistente)

## Opción A — Un solo doble clic

En la raíz del repo está **`EJECUTAR - EASYOCR.bat`**:

- **Doble clic** → corre todo con 10 actas (~15 min, casi todo es el OCR).
- Desde una terminal (cmd o PowerShell) puedes elegir el tamaño:
  ```
  cd onpe_actas
  EJECUTAR - EASYOCR.bat 50
  ```
- Al final, los resultados quedan en `data\corrida\`:
  - `analisis.json` → **exactitud por campo con IC 95%** (el número que importa)
  - `evaluacion.json` → detalle por acta y por campo (errores uno a uno)
  - `salida\<mesa>.json` → la lectura estructurada de cada acta
  - `muestra.json` → qué mesas cayeron en el sorteo (semilla 2026, reproducible)

## Opción B — Etapa por etapa (para entender qué hace cada una)

**Regla de oro de esta máquina:** Python deberia estar instalado en la maquina.


Luego, desde la raíz del repo, cada etapa se corre DENTRO de su carpeta
(los scripts usan rutas relativas a propósito — OpenCV en Windows no abre
rutas absolutas con tildes como "Visión"):

```bat
cd src\scraper
%PY% muestreo_nacional.py --n 10 --seed 2026 --out ..\..\data\corrida
%PY% pdf_to_images.py --in ..\..\data\corrida\raw_pdf --out ..\..\data\corrida\raw_img --dpi 300

cd ..\preprocessing
%PY% preprocess.py --in ..\..\data\corrida\raw_img --out ..\..\data\corrida\processed

cd ..\detection
%PY% regiones_plantilla.py --in ..\..\data\corrida\processed --out ..\..\data\corrida\crops
:: (borrar las carpetas *_p0 y *_p1 de crops: son actas electrónicas, no van al OCR)

cd ..\pipeline
%PY% piloto_10_actas.py --modo limpio --crops ..\..\data\corrida\crops --gt ..\..\data\corrida\ground_truth --out ..\..\data\corrida\salida
%PY% evaluar_salidas.py --salidas ..\..\data\corrida\salida --gt ..\..\data\corrida\ground_truth --regla-cero --out ..\..\data\corrida\evaluacion.json
%PY% analisis_estadistico.py --eval ..\..\data\corrida\evaluacion.json --muestra ..\..\data\corrida\muestra.json --out ..\..\data\corrida\analisis.json
```

Extras útiles:
- **Ver la plantilla sobre un acta** (overlay de calibración):
  `cd src\detection && %PY% regiones_plantilla.py --debug --img ..\..\data\corrida\processed\acta_presidencial_XXXXXX.png`
- **Actas electrónicas (STAE) sin OCR**:
  `cd src\scraper && %PY% extraer_electronicas.py --tipos ..\..\data\corrida\tipos.json ...`
  (requiere generar antes `tipos.json`; ver EVALUACION_NACIONAL.md)
- **OCR en paralelo** (4 terminales, cada una con un cuarto de las actas):
  añade `--slice 0/4`, `--slice 1/4`, etc. al comando de `piloto_10_actas.py`.

## Compilar el paper

```bat
cd paper
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```
(2 pasadas; `main_es.tex` para la versión en español. MiKTeX ya está
instalado y en el PATH; baja solo los paquetes que falten.)

## Problemas comunes

| Síntoma | Causa y solución |
|---|---|
| `No module named 'encodings'` | Falta `set PYTHONHOME=C:\ProgramData\anaconda3` |
| `UnicodeEncodeError ... charmap` | Falta `set PYTHONUTF8=1` |
| Descarga devuelve HTML / error | El portal ONPE exige huella de Chrome: ya lo maneja `curl_cffi`; revisa internet o espera y reintenta |
| Primera corrida del OCR lenta | EasyOCR descarga sus modelos (~100 MB) solo la primera vez |
| `cv2.imread` devuelve None | Estás usando rutas absolutas con tildes; corre desde la carpeta del módulo con rutas relativas |
| Plantilla desalineada en un acta | Verifica con `--debug`; el registro fiducial debería corregirla sola |
