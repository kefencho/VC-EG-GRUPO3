# Informe del Piloto de Viabilidad — 10 actas de punta a punta

> **Objetivo:** demostrar que el pipeline propuesto (acta digitalizada →
> preprocesamiento → detección de regiones → reconocimiento → JSON) es viable
> con **datos reales** del proceso EG2026, medir su desempeño con métricas
> objetivas y detectar los riesgos técnicos antes de la versión final.
>
> Ejecutado: 02/03-jul-2026 · 10 actas presidenciales (mesas 000001–000010,
> Chachapoyas, Amazonas) · hardware: laptop sin GPU.

## 1. Qué se probó (las 5 etapas, con datos reales)

| Etapa | Implementación | Resultado |
|---|---|---|
| 1. Adquisición | `src/scraper/download_actas.py` — API real del portal ONPE (`resultadoelectoral.onpe.gob.pe`), cadena buscar/mesa → detalle → archivo tipo 1 (ACTA DE ESCRUTINIO) → URL firmada S3; `curl_cffi` impersonate chrome124 para pasar el WAF | 10/10 PDFs descargados (~30 s) |
| 2. Preprocesamiento | `pdf_to_images.py` (300 DPI) + `preprocess.py` (deskew, CLAHE, denoise) | 10/10 imágenes procesadas |
| 3. Detección | `src/detection/regiones_plantilla.py` — **regiones por plantilla**: el acta tiene layout fijo, 46 regiones definidas como fracciones de página y calibradas visualmente sobre la mesa 000001 (`--debug` genera el overlay) | 46 recortes/acta, calce visual correcto (fig. `figuras/plantilla_overlay.png`) |
| 4. Reconocimiento | EasyOCR (allowlist de dígitos) sobre cada recorte, con variantes de limpieza (ver §3) | ver tabla §4 |
| 5. Salida estructurada | JSON por acta (`data/salida*/<mesa>.json`) con el esquema de la propuesta | 10/10 JSON emitidos |


## 2. Ground truth sin anotación manual (hallazgo metodológico)

El mismo portal que publica el PDF publica los **votos oficiales digitados**
(JSON de la API). `src/scraper/ground_truth.py` los guarda por mesa y la
evaluación compara la lectura OCR contra ese oficial — reproducible y sin
sesgo de anotador. Verificado a ojo contra el acta 000001 (blancos=29,
nulos=17, emitidos=180 ✓).

**Sutileza detectada:** las posiciones 04 y 14 del formulario están vacías
(partidos retirados; votos `null` en la API). Se **excluyen** de la evaluación:
contarlas producía aciertos espurios (`null == null`). Quedan **43 campos
evaluables por acta** (36 partidos + blancos/nulos/impugnados/emitidos +
electores + mesa + ciudadanos) = 430 en el piloto.

## 3. Iteraciones de reconocimiento (análisis de errores dirigido)

- **v1 básico:** EasyOCR directo sobre el recorte (upscale 2×).
- **v2 tinta:** análisis de errores de v1 → los bordes impresos y el fondo se
  leían como dígitos. Se aísla la tinta (umbral de oscuridad), margen interior
  anti-bordes y lectura por sub-cajas en campos con casillas.
- **v3 plantilla:** la inspección visual (fig. `figuras/limpieza_celdas.png`)
  mostró que los separadores punteados de la celda son **oscuros** (un umbral
  no los elimina) → se borran **por posición de plantilla** (fracciones 0.31 y
  0.70 del ancho de celda); Otsu por celda (robusto al sombreado alterno de
  filas) y filtro de motas.
- **v4 regla de dominio:** en varias actas los miembros de mesa **dejan la
  celda vacía en lugar de escribir 0**. "Celda sin trazo = 0 votos" es
  semántica del formulario, no visión; se aplica como post-proceso
  (`evaluar_salidas.py --regla-cero`) y se reporta por separado.

## 4. Resultados (10 actas, 430 campos, vs. oficial ONPE)

| Versión | Exactitud por campo | CER | Campos correctos |
|---|---:|---:|---:|
| v1 básico | 43.95% | 0.524 | 189/430 |
| v2 aislar tinta | 52.09% | 0.419 | 224/430 |
| v3 limpieza por plantilla | 52.79% | 0.476 | 227/430 |
| **v4 = v3 + regla "vacío=0"** | **58.37%** | **0.420** | **251/430** |

Tiempo de OCR: ~60 s/acta (CPU). Detalle por acta y por campo en
`docs/resultados/evaluacion_v*.json` (re-evaluables sin re-correr OCR con
`src/pipeline/evaluar_salidas.py`).

### Taxonomía de errores residuales
1. **Dígitos manuscritos sueltos no detectados** (1, 4, 0 pequeños → sin lectura).
2. **Dígito extra residual** cuando el trazo invade la franja del separador.
3. **Confusiones de forma** (8↔18, 22→212 en trazos anchos, 7↔9).
4. **Campos de casillas múltiples** (total de ciudadanos) aún inestables.

## 5. Conclusiones de viabilidad

1. **El pipeline es viable de punta a punta con datos reales**: descarga
   automatizada, preprocesamiento, localización de los 43 campos, lectura y
   JSON estructurado funcionan hoy, sin anotación manual y sin GPU.
2. **La evaluación es sólida y gratuita**: ground truth oficial de la API +
   métricas CER/exactitud por campo — la versión final ya tiene su protocolo
   experimental definido.
3. **El cuello de botella es el reconocedor**, no la detección ni los datos:
   el OCR genérico (EasyOCR) se estanca en ~53–58% de exactitud por campo
   sobre manuscrito peruano real. Las mejoras clásicas de visión (umbrales,
   plantilla, morfología) aportan +9 puntos y saturan.
4. **Implicación directa para la versión final** (alineada con el Related
   Work): fine-tuning de un reconocedor transformer (TrOCR/DTrOCR-style) con
   los pares (recorte, valor oficial) que este mismo piloto genera — cada acta
   descargada produce ~43 ejemplos etiquetados gratis; 1,000 actas ≈ 43,000
   ejemplos de entrenamiento.

## 6. Próximos pasos
1. Escalar el scraper (500–1,000 actas) → dataset de entrenamiento con etiquetas automáticas (plantilla + oficial API).
2. Fine-tuning de TrOCR sobre los recortes de dígitos manuscritos; comparar EasyOCR vs PaddleOCR vs TrOCR con la misma evaluación.
3. Experimento de etiquetado few-shot con LLM (sugerencia de la profesora): comparar valores LLM vs oficial API en una muestra.
4. Redactar el paper final en formato WVC (IEEE 2 columnas, máx. 6 páginas, abstract en inglés ≤150 palabras) usando estos resultados como sección de Experiments.
