# Experimento: etiquetado / lectura con LLM multimodal (few-shot)

> Experimento sugerido por la profesora ("pueden usar un LLM con visión, darle
> unos ejemplos en JSON y que etiquete las demás actas"). Aquí se implementa y
> se compara, con rigor, contra el pipeline clásico. Ejecutado: 09-jul-2026.

## 1. Diseño

- **Modelo:** Gemini 2.5 Flash (multimodal), free tier, vía REST.
  Código: `src/recognition/llm_ocr.py`.
- **Enfoque end-to-end (sin plantilla ni OCR):** se le pasa la imagen del acta
  **completa** más **2 ejemplos few-shot** (imagen + su JSON de votos oficiales)
  y se le pide devolver el JSON de la nueva acta. El LLM localiza y lee.
- **Muestra:** 15 actas manuscritas de la muestra nacional (las 2 primeras se
  usan como ejemplos, no se evalúan). Imágenes reducidas a 1600 px, JPEG.
- **Evaluación idéntica al pipeline:** exactitud por campo y CER contra el
  ground truth oficial de la API ONPE, excluyendo las filas vacías del
  formulario (posiciones 04/14). 43 campos por acta.

## 2. Resultado — cara a cara sobre las MISMAS 15 actas

| Método | Exactitud por campo | CER |
|---|---:|---:|
| **Pipeline (plantilla registrada + EasyOCR)** | **60.93%** (393/645) | ~0.40 |
| LLM few-shot (Gemini 2.5 Flash, end-to-end) | 48.37% (312/645) | 0.591 |

**El pipeline clásico gana por ~12.5 puntos.** Contraintuitivo pero explicable
(§3). Detalle por acta en `docs/resultados/evaluacion_llm_gemini.json`.

## 3. Lectura crítica (lo que se dice en la exposición)

1. **El LLM no está entrenado para dígitos manuscritos peruanos.** Lee el acta
   como un todo y "razona" el layout, pero en celdas de un dígito manuscrito el
   OCR especializado (EasyOCR) es más preciso. Coincide con la literatura del
   Related Work: DTrOCR muestra que el reconocimiento fuerte de manuscrito
   requiere **entrenamiento específico**, no solo un modelo general potente.
2. **Se hunde en las actas de baja calidad** igual que el OCR, pero más: las
   dos peores (013912, 015264: sombreado/contraste malo) caen a 21–23% (vs
   35–53% del pipeline). Sin celdas aisladas, el ruido lo confunde más.
3. **Su ventaja real es otra:** funciona **sin plantilla, sin registro y sin
   anotación de posiciones** — donde el pipeline necesitó calibrar la plantilla
   y los fiduciales, el LLM solo necesitó 2 ejemplos. Es **cero ingeniería de
   detección**. Para un proceso electoral nuevo con otro formato de acta, el
   LLM arranca de inmediato; el pipeline hay que recalibrarlo.
4. **Costo y reproducibilidad:** free tier (costo ~0), pero depende de un
   servicio externo (hubo errores 503 transitorios por saturación) y de que el
   proveedor no cambie el modelo — el pipeline es 100% local y determinista.

## 4. Conclusión para el proyecto

El experimento **responde la sugerencia de la profesora con evidencia**: el LLM
few-shot es **viable pero hoy inferior** al pipeline clásico en exactitud de
dígitos manuscritos (48% vs 61%). Su valor no es reemplazar al pipeline sino:
(a) **arrancar sin anotación** cuando no hay plantilla; (b) generar un
**etiquetado inicial** que un humano corrige (más rápido que anotar desde
cero); (c) leer los **campos de contexto** (mesa, departamento) donde acierta
más. La recomendación del proyecto se mantiene: para producción, **fine-tuning
de un reconocedor especializado** (TrOCR) sobre los recortes; el LLM como
herramienta de arranque y de pre-anotación.

## 5. Reproducción
1. **Ejecución recomendada.**
En la raíz del repo está **`EJECUTAR - LLM.bat`**:

- **Doble clic** → corre todo con 15 actas.
- Desde una terminal (cmd o PowerShell) puedes elegir el tamaño:
2. **Ejecución manual.**
```bash
# requiere onpe_actas/.env con GEMINI_API_KEY (free tier, NO se versiona)
cd src/recognition
python llm_ocr.py --n 15 --shots 2 --out ../../data/muestra/salida_llm
```
Evidencia: `docs/resultados/evaluacion_llm_gemini.json`.
