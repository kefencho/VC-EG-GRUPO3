# Related Work — Trabajos Relacionados (Grupo 3, Sección B)

> Guía de estudio para la tarea **Related Work Exploration** (Prof. Elian Laura).
> Tres papers de congresos top-tier (CVPR/WACV 2024, vía openaccess.thecvf.com),
> leídos completos y verificados cifra por cifra contra el texto original.
> Los PDF oficiales están en `docs/papers/` (rtdetr.pdf, dtrocr.pdf, omniparser.pdf).

**Proyecto que sustentan:** Detección y Reconocimiento Automático de Resultados
Electorales en Actas de Escrutinio de las Elecciones Generales del Perú 2026
(pipeline: acta digitalizada → preprocesamiento → detección de regiones →
reconocimiento OCR → JSON estructurado).

| # | Paper | Venue | Etapa del pipeline que sustenta |
|---|-------|-------|--------------------------------|
| 1 | RT-DETR — *DETRs Beat YOLOs on Real-time Object Detection* | CVPR 2024 | Etapa 3: detección de regiones (YOLOv11 vs Faster R-CNN vs DETR) |
| 2 | DTrOCR — *Decoder-only Transformer for Optical Character Recognition* | WACV 2024 | Etapa 4: reconocimiento de valores impresos y manuscritos |
| 3 | OmniParser — *A Unified Framework for Text Spotting, KIE and Table Recognition* | CVPR 2024 | Etapas 3–5: alternativa end-to-end (tabla + campos clave + salida estructurada) |

---

## Paper 1 — RT-DETR: *DETRs Beat YOLOs on Real-time Object Detection* (CVPR 2024)

**Cita (APA 7):** Zhao, Y., Lv, W., Xu, S., Wei, J., Wang, G., Dang, Q., Liu, Y., & Chen, J. (2024). DETRs beat YOLOs on real-time object detection. En *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 16965–16974). IEEE.

- Página: <https://openaccess.thecvf.com/content/CVPR2024/html/Zhao_DETRs_Beat_YOLOs_on_Real-time_Object_Detection_CVPR_2024_paper.html>
- PDF local: `docs/papers/rtdetr.pdf`
- Verificación: **aprobado sin correcciones** (cita y cifras cotejadas contra el paper).

### Problema
Los YOLO dominan la detección en tiempo real pero dependen del post-procesamiento
NMS (Non-Maximum Suppression), que ralentiza la inferencia e introduce dos
hiperparámetros (umbral de confianza y de IoU) que hacen inestables velocidad y
exactitud. Los DETR eliminan el NMS gracias a la asignación uno-a-uno, pero eran
demasiado costosos para tiempo real. RT-DETR resuelve el dilema: el primer
detector end-to-end en tiempo real, y además propone medir la velocidad
"end-to-end" (incluyendo el NMS) para comparar detectores de forma justa.

### Método (para re-explicar en clase)
Dos pasos: primero velocidad, luego exactitud.

1. **Encoder híbrido eficiente.** El cuello de botella de los DETR multi-escala
   es el encoder Transformer (en Deformable-DETR consume el 49% de los GFLOPs y
   aporta solo el 11% del AP). La solución desacopla dos operaciones: la
   interacción *intra-escala* se hace con atención (**AIFI**) solo sobre S5 (la
   escala de mayor nivel semántico — atender las escalas bajas es redundante), y
   la fusión *entre escalas* se hace con convoluciones (**CCFF**, estilo PANet
   con bloques RepConv).
2. **Selección de queries por mínima incertidumbre.** La selección clásica elige
   las top-K características solo por score de clasificación (entran cosas bien
   clasificadas pero mal localizadas). Aquí la incertidumbre se define como la
   discrepancia entre las distribuciones de localización y clasificación,
   U(X̂)=||P(X̂)−C(X̂)||, y se optimiza en la pérdida: las queries iniciales del
   decoder salen buenas en ambas cosas.
3. **Bonus práctico:** se pueden quitar capas del decoder en inferencia para
   ganar velocidad sin re-entrenar (5 capas en vez de 6: −0.1% AP, −0.5 ms).

### Arquitectura
Backbone CNN (ResNet-50/101) → encoder híbrido (AIFI + CCFF) sobre {S3, S4, S5}
→ decoder Transformer con K=300 object queries y matching bipartito (sin anclas,
sin NMS). Entrada 640×640.

### Resultados clave (cifras exactas, verificadas)
- **RT-DETR-R50: 53.1% AP y 108 FPS** (COCO val2017, GPU T4 TensorRT FP16); R101: 54.3% AP y 74 FPS — superan a los YOLO L/X comparados en exactitud Y velocidad.
- Vs DINO-Deformable-DETR-R50: **+2.2% AP (53.1 vs 50.9) y ~21× más rápido** (108 vs 5 FPS).
- Con pre-entrenamiento en Objects365: 55.3%/56.2% AP (R50/R101).
- Costo del NMS (YOLOv8): con conf=0.001 el NMS tarda ~2.36 ms; subir conf a 0.05 baja el AP a 51.2% — exactitud y velocidad dependen de umbrales manuales.
- Ablaciones: encoder híbrido +1.5% AP con −24% latencia; query selection por incertidumbre +0.8% AP (48.7 vs 47.9).

### Limitaciones
- Peor en **objetos pequeños** que los mejores YOLO (−0.5% AP_S vs YOLOv8-L; −0.9% vs YOLOv7-X) — declarado por los autores.
- Evaluado solo en COCO/Objects365 (objetos naturales): **no evalúa documentos ni manuscrito**.
- FPS medidos en un stack específico (T4 + TensorRT FP16); no se trasladan directo a otros entornos.
- Requiere 72 épocas de entrenamiento (vs 36 de DINO).

### Conexión con nuestro proyecto
Responde exactamente la disyuntiva de la etapa 3 (YOLOv11 vs Faster R-CNN vs
DETR): demuestra que un DETR bien diseñado ya no pierde en velocidad y aporta
una ventaja estructural para actas — **sin NMS no hay umbrales manuales** cuya
mala calibración borre o duplique campos en una tabla de celdas contiguas con
sellos y firmas superpuestos; una salida determinista favorece la trazabilidad
exigible en un contexto electoral. Además nos da la **metodología de comparación
justa** (benchmark de velocidad end-to-end, con NMS incluido) que aplicaremos al
comparar candidatos con mAP y latencia. Honestidad: no evalúa documentos, así
que legitima al DETR como candidato serio y nos dice cómo compararlo — no le
adjudica la victoria; y su debilidad en objetos pequeños obliga a validar los
campos chicos del acta (mitigable con más resolución o recorte por regiones).

### Glosario rápido
- **NMS:** post-procesamiento que elimina cajas superpuestas; requiere umbrales de confianza e IoU.
- **Detector end-to-end:** predice el conjunto final de objetos vía matching bipartito, sin anclas ni NMS.
- **Object query:** vector que el decoder DETR refina capa a capa hasta volverlo predicción (clase + caja).
- **AIFI:** atención solo dentro de la escala S5 (alto nivel semántico).
- **CCFF:** fusión convolucional entre escalas, estilo PANet con RepConv.
- **AP (COCO):** precisión promedio sobre IoU 0.5–0.95; AP_S/M/L la desglosa por tamaño de objeto.
- **TensorRT FP16:** motor de inferencia NVIDIA en precisión media; entorno estándar de los FPS del paper.

### Preguntas probables de la profesora (con respuesta)
1. **¿Cómo demuestran que el NMS realmente perjudica a los YOLO?** Miden en YOLOv8 el AP y el tiempo del kernel EfficientNMS: con conf=0.001 logra su mejor AP pero ~2.36 ms de NMS; con conf=0.05 baja a 51.2% AP aunque el NMS cae a 1.06 ms. Exactitud y velocidad dependen de umbrales manuales; por eso proponen medir la velocidad end-to-end.
2. **¿Por qué el encoder híbrido desacopla intra-escala de cross-escala?** Porque el encoder multi-escala era el cuello de botella (49% de GFLOPs, 11% del AP): las características altas ya derivan de las bajas, atender todo junto es redundante. La ablación lo prueba: la variante final da +1.5% AP con 24% menos latencia.
3. **¿Qué aporta la selección de queries por mínima incertidumbre?** +0.8% AP (48.7 vs 47.9): en vez de elegir por score de clasificación solamente, exige consistencia entre clasificación y localización, optimizándola por gradiente en la pérdida.
4. **¿Cuál es su principal limitación para nuestro caso?** Objetos pequeños (−0.5/−0.9% AP_S) y que todo se evaluó en COCO, no en documentos. Los campos-región del acta son grandes (riesgo moderado), pero validaremos los campos chicos con nuestro dataset.
5. **Si solo se probó en COCO, ¿por qué citarlo?** Porque legitima al DETR en tiempo real como candidato (53.1% AP, 108 FPS, 21× más rápido que DINO) y nos da la metodología de comparación justa. No afirmamos que gane en actas: eso lo mediremos nosotros.

---

## Paper 2 — DTrOCR: *Decoder-only Transformer for Optical Character Recognition* (WACV 2024)

**Cita (APA 7):** Fujitake, M. (2024). DTrOCR: Decoder-only Transformer for optical character recognition. En *Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)* (pp. 8025–8035). IEEE/CVF.

- Página: <https://openaccess.thecvf.com/content/WACV2024/html/Fujitake_DTrOCR_Decoder-Only_Transformer_for_Optical_Character_Recognition_WACV_2024_paper.html>
- PDF local: `docs/papers/dtrocr.pdf`
- Verificación: **aprobado con 2 correcciones** (ya aplicadas abajo: volumen de preentrenamiento ~10 mil millones, y SROIE descrito sin mención de sellos).

### Problema
El OCR clásico usa encoder-decoder: un codificador visual (CNN/ViT) extrae
características y un decodificador las traduce a texto; para robustez se añaden
modelos de lenguaje externos, rectificación y superresolución, encareciendo
todo. El paper pregunta: ¿es necesario el codificador visual? ¿Puede un modelo
de lenguaje generativo preentrenado (tipo GPT) reconocer texto por sí solo?
(TrOCR usa preentrenamiento por enmascaramiento MLM, no generativo.)

### Método (para re-explicar en clase)
**Elimina el codificador visual por completo.** Un patch embedding (de ViT)
redimensiona la imagen a 128×32, la corta en parches de 8×4 y convierte cada
parche en un "token visual". Esa secuencia entra a un **GPT-2 preentrenado**
que, tras un token [SEP], genera el texto reconocido token a token
(autorregresivo, con beam search) hasta [EOS]. Imagen y texto conviven en la
misma secuencia: la autoatención enmascarada reemplaza a la atención cruzada.

Entrenamiento en dos fases: (1) preentrenamiento con **~10 mil millones de
imágenes sintéticas** (4B escena horizontales + 2B verticales + 100M multilínea
con SynthTIGER; 2B impresas con Text Render; 2B manuscritas con TRDG y 5,427
fuentes de estilo manuscrito) en proporción 60% escena / 20% impreso / 20%
manuscrito; (2) fine-tuning con datos reales de cada tarea.

### Arquitectura
Patch embedding + GPT-2 de 12 capas, 768 dimensiones, 12 cabezas (~128M
parámetros), vocabulario BPE. Sin CNN, sin ViT encoder, sin atención cruzada.
Con GPT-2 Medium (359M) y Large (778M) la exactitud sube de 97.7 a 97.9 y 98.3.

### Resultados clave (cifras exactas, verificadas)
- **Escena (inglés, sintéticos):** IIIT5K 98.4, SVT 96.9, IC13 98.8/97.8, IC15 92.3/90.4, SVTP 95.0, CUTE 97.6 — supera a PARSeq, TrOCR_LARGE y MaskOCR_LARGE.
- **SROIE Task 2 (recibos escaneados, texto impreso): F1 98.37** — supera a TrOCR_LARGE (96.58).
- **IAM Handwriting (manuscrito): CER 2.38 sin LM externo** — mejor que TrOCR_LARGE (2.89) en las mismas condiciones y que Diaz et al. (2.75, que usaba datos internos + LM externo).
- **Chino (benchmark CTR):** Escena 87.4, Web 89.7, Documento 99.9, Manuscrito 81.4 con 105M parámetros — aplasta a MaskOCR_LARGE (76.2/76.8/99.4/67.9 con 318M).
- **Ablación decisiva (Tabla 5):** sin encoder 97.7 STR; añadir un ViT encoder da 97.5 (casi igual); TrOCR (ViT+RoBERTa con MLM) queda en 92.6 → **el preentrenamiento generativo supera al MLM**.
- **Ablación de datos (Tabla 7):** con solo 25% del preentrenamiento, cae de 97.7 a 91.4 (STR) — el volumen sintético es crítico.

### Limitaciones
- **Velocidad:** generación autorregresiva → 97.9 FPS vs 751 FPS de CRNN.
- Depende de un preentrenamiento sintético masivo (~10 mil millones de imágenes); costoso de reproducir.
- Solo reconoce **texto ya recortado** (líneas/palabras): no detecta ni analiza layout — nuestra etapa 3 sigue siendo necesaria.
- Evaluado solo en inglés y chino; **no evalúa español ni campos puramente numéricos**; el manuscrito del preentrenamiento es sintético (fuentes tipográficas), no caligrafía real.
- Trabajo de un solo autor (laboratorio industrial), sin código público.

### Conexión con nuestro proyecto
Sustenta la etapa 4 (candidatos PaddleOCR, TrOCR, Donut): evidencia de que los
reconocedores Transformer con modelo de lenguaje preentrenado dominan los tres
regímenes que coexisten en un acta — **impreso** (SROIE F1 98.37, recibos
escaneados: dominio de documento real análogo al acta), **manuscrito** (IAM CER
2.38, superando a TrOCR en las mismas condiciones) y **texto degradado u
ocluido** (la Figura 3 muestra robustez ante oclusión en texto de escena — un
indicio extrapolable a los sellos y firmas del acta, aunque el paper no lo
demuestra en documentos). Usa exactamente **CER**, nuestra métrica. La ablación
95.3→97.7 al añadir datos reales respalda nuestra decisión de anotar actas
reales para el fine-tuning. Advertencia metodológica: el prior lingüístico del
GPT podría "corregir" dígitos hacia secuencias plausibles — hay que vigilarlo
al reconocer números sin contexto gramatical.

### Glosario rápido
- **Decoder-only:** Transformer con solo el bloque decodificador; entrada y salida en una misma secuencia.
- **Autorregresivo:** genera token por token, realimentando cada predicción, hasta [EOS].
- **Patch embedding:** corta la imagen en parches (8×4) y los convierte en "tokens visuales".
- **Preentrenamiento generativo (GPT):** predecir el siguiente token en corpus enormes.
- **MLM:** preentrenamiento por enmascaramiento (BERT/RoBERTa, usado por TrOCR); rinde peor para OCR.
- **Beam search:** decodificación que mantiene las k secuencias más probables.
- **CER:** tasa de error por carácter (inserciones+borrados+sustituciones) — la métrica de nuestro proyecto.

### Preguntas probables de la profesora (con respuesta)
1. **¿Cómo reconoce texto sin codificador visual?** El patch embedding convierte la imagen en tokens visuales que el GPT-2 procesa como si fueran texto; la autoatención enmascarada aprende la relación imagen-texto durante el preentrenamiento masivo. La Tabla 5 confirma que añadir un ViT encoder casi no mejora (97.5 vs 97.7).
2. **¿Diferencia con TrOCR?** TrOCR es encoder-decoder (ViT + RoBERTa con atención cruzada) y preentrena con MLM; DTrOCR elimina el encoder y preentrena generativamente. Comparación controlada: 97.7 vs 92.6 en STR.
3. **¿Qué evidencia hay en manuscrito?** IAM CER 2.38 sin LM externo, mejor que TrOCR_LARGE (2.89) y que Diaz et al. (2.75). Sólida en líneas manuscritas en inglés; ojo: no evalúa dígitos manuscritos ni español.
4. **¿Desventaja práctica principal?** Velocidad (97.9 vs 751 FPS de CRNN) y dependencia de ~10 mil millones de imágenes sintéticas (con 25% de datos cae a 91.4). Mitigable con cuantización int8, dice el autor.
5. **¿Qué NO debemos extrapolar al proyecto?** Que funcione sin ajuste en dígitos manuscritos en español: no evalúa ese caso, requiere campos ya recortados, y el prior lingüístico puede sesgar dígitos. Por eso: fine-tuning y validación con actas reales anotadas.

---

## Paper 3 — OmniParser: *A Unified Framework for Text Spotting, Key Information Extraction and Table Recognition* (CVPR 2024)

**Cita (APA 7):** Wan, J., Song, S., Yu, W., Liu, Y., Cheng, W., Huang, F., Bai, X., Yao, C., & Yang, Z. (2024). OmniParser: A unified framework for text spotting, key information extraction and table recognition. En *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 15641–15653). IEEE/CVF.

- Página: <https://openaccess.thecvf.com/content/CVPR2024/html/Wan_OmniParser_A_Unified_Framework_for_Text_Spotting_Key_Information_Extraction_CVPR_2024_paper.html>
- PDF local: `docs/papers/omniparser.pdf`
- Verificación: **aprobado con 2 correcciones** (ya aplicadas abajo: pasos de fine-tuning por tarea, y la nota metodológica de SROIE es una daga †, no asterisco).

### Problema
El *Visually-situated Text Parsing* (VsTP) agrupa tres tareas: detectar y leer
texto (text spotting), extraer campos clave (KIE) y reconocer tablas (TR).
Antes de este paper cada una usaba arquitecturas y objetivos propios: los
especialistas son precisos pero fragmentan el pipeline; los generalistas (LLMs
multimodales) son versátiles pero menos precisos, dependen de OCR externo y no
dan localización verificable. OmniParser: **un solo modelo, un solo objetivo,
una sola representación para las tres tareas**.

### Método (para re-explicar en clase)
Convierte las tres tareas en **generación de secuencias condicionada por
puntos**: los puntos centrales de cada texto son el puente entre estructura y
contenido. Dos etapas:

1. **Structured Points Decoder:** genera autorregresivamente la "secuencia de
   puntos estructurados" — coordenadas (x,y) del centro de cada texto,
   cuantizadas como tokens discretos, intercaladas con tokens estructurales de
   la tarea (`<tr>`, `<td>` con colspan para tablas; `<address>`, `<date>` para
   KIE).
2. **Region Decoder + Content Decoder (en paralelo por punto):** desde cada
   punto central, uno genera el polígono de 16 puntos y el otro la
   transcripción carácter a carácter.

Desacoplar estructura y contenido acorta las secuencias radicalmente: evita la
acumulación de error de Donut, que genera todo el HTML (texto incluido) en una
sola secuencia larguísima. Preentrenamiento con dos estrategias de prompting:
**spatial-window** (leer solo lo que cae en una ventana espacial → percepción de
coordenadas) y **prefix-window** (emitir solo textos que empiezan con ciertos
caracteres → semántica a nivel de carácter).

### Arquitectura
Encoder Swin-B (preentrenado en ImageNet-22k) + FPN multi-escala → tres
decodificadores Transformer de arquitectura idéntica pero **parámetros
independientes** (compartirlos degrada: 82.5 vs 84.0), cada uno con 4 capas, 8
cabezas, dimensión 512. La tarea se elige solo con el prompt; la salida JSON
(KIE) o HTML (tablas) se arma desde la secuencia generada. Entrenamiento: 700k
pasos de preentrenamiento (500k a 768×768 + 200k a 1920×1920); fine-tuning de
20k pasos para spotting, 200k para KIE, y en tablas 400k (puntos) + 200k
(contenido).

### Resultados clave (cifras exactas, verificadas)
- **Text spotting:** Total-Text E2E 'None' 84.0 (nuevo SOTA, +1.5% sobre DeepSolo 82.5); CTW1500 'None' 66.8 (SOTA); ICDAR2015 Strong 89.6.
- **KIE:** CORD F1 84.8 (vs Donut 84.1); SROIE accuracy TED 93.6† vs Donut 92.8 († = los autores generaron las localizaciones porque SROIE no las provee).
- **Tablas — el dato estrella:** PubTabNet TEDS **88.83 vs Donut 22.7** (Donut reproducido, decoder de 4,000 tokens); FinTabNet TEDS 89.75 vs Donut 29.1. Donut colapsa en tablas largas por acumulación de error; el diseño de dos etapas no.
- Velocidad en tablas: 1.3 FPS vs 0.8 FPS de Donut.
- Ablaciones: spatial-window +0.5, prefix-window +1.1 (82.4→84.0 combinadas); Swin-B vs ResNet50: 84.0 vs 82.1.

### Limitaciones
- Requiere **puntos centrales anotados** para entrenar (los autores lo declaran); tendríamos que anotarlos en las actas.
- No modela elementos no textuales (figuras, sellos, firmas serían ruido no modelado).
- **No evalúa manuscrito ni español** — todos sus benchmarks son texto impreso (escena, recibos, PDFs).
- En CORD, Donut le gana en accuracy TED (90.9 vs 88.0): no gana en todas las métricas de KIE.
- Velocidad moderada (1.3 FPS en tablas) y entrenamiento costoso (700k pasos + fine-tuning por tarea).

### Conexión con nuestro proyecto
Sustenta la **alternativa end-to-end** para las etapas 3–5: un único modelo que
recibe el acta y emite directamente la estructura — la tabla de resultados vía
TR (HTML con celdas ancladas a puntos) y los campos clave (mesa, votos, totales)
vía KIE — exactamente el JSON final que exige el proyecto. Frente a Donut (el
candidato end-to-end de nuestra tabla) su ventaja es doble y medible: (1)
**localización explícita de cada valor extraído** (punto + polígono), que
permite auditar visualmente sobre el acta cada cifra del JSON — trazabilidad
crítica en un contexto electoral; y (2) **robustez en tablas largas** (TEDS
88.83 vs 22.7 de Donut en PubTabNet), el mismo problema que tendría un acta con
~20 filas de partidos. Honestidad: no evalúa manuscrito ni español; adoptarlo
exigiría fine-tuning con actas anotadas (incluyendo puntos centrales) y
validación propia de CER/WER — por eso lo posicionamos como alternativa a
comparar contra el pipeline modular, no como solución probada.

### Glosario rápido
- **VsTP:** extraer información estructurada de imágenes ricas en texto.
- **Text spotting:** detectar dónde está cada texto y leerlo, end-to-end.
- **KIE:** extraer campos con significado (fecha, total…) asignando cada valor a su entidad.
- **TR (TSR/TCR):** reconocer estructura de tabla (filas/columnas/celdas) y su contenido.
- **Secuencia de puntos estructurados:** centros de texto cuantizados + etiquetas estructurales; el puente estructura↔contenido.
- **TEDS / S-TEDS:** similitud de tablas por distancia de edición entre árboles HTML (S-TEDS: solo estructura).
- **Cuantización de coordenadas:** convertir (x,y) continuas en tokens discretos para que un decodificador "escriba" posiciones.

### Preguntas probables de la profesora (con respuesta)
1. **¿Por qué dos etapas y no una sola secuencia como Donut?** Desacoplar estructura y contenido acorta las secuencias: la etapa 1 solo emite puntos y etiquetas; la 2 genera polígonos y texto en paralelo. Evita la acumulación de error de secuencias largas: Donut (4,000 tokens) logra TEDS 22.7 en PubTabNet; OmniParser (1,500) logra 88.83. Y cada valor queda anclado a una posición: interpretable.
2. **¿Qué aportan spatial-window y prefix-window prompting?** Percepción espacial y semántica de carácter, respectivamente. Ablación en Total-Text: 82.4 base → 82.9 → 83.5 → 84.0 con ambas.
3. **Donut le gana en accuracy en CORD (90.9 vs 88.0), ¿por qué defender OmniParser?** Gana en F1 de campo en CORD (84.8 vs 84.1) y en SROIE (93.6† vs 92.8); es el único generativo que además **localiza** cada entidad (auditable); y se preentrenó solo con texto de escena (mejor generalización).
4. **¿Limitaciones para las actas ONPE?** No evalúa manuscrito ni español; exige puntos centrales anotados; no modela sellos/firmas; 1.3 FPS importa a escala de miles de actas. Todo eso lo validaríamos con fine-tuning y CER/WER propios.
5. **¿Puntos centrales vs bounding boxes de YOLO/DETR?** Los puntos son más baratos de anotar y manejan texto curvo (el polígono se reconstruye después); la contrapartida es detección autorregresiva (más lenta) y sin scores de confianza directos por región. A cambio integra detección+reconocimiento+estructura en un solo modelo con salida JSON/HTML — lo que nuestro pipeline modular arma en tres etapas.

---

## Síntesis transversal (lo que la tarea pide identificar)

**Métodos comunes:** los tres son Transformers y los tres atacan el mismo
trade-off exactitud/velocidad con la misma estrategia — reemplazar componentes
artesanales por diseño end-to-end (RT-DETR elimina el NMS; DTrOCR elimina el
codificador visual; OmniParser elimina el pipeline multi-modelo). Los tres usan
generación/predicción condicionada y ablaciones sistemáticas para justificar
cada componente.

**Datasets comunes:** COCO (detección), SROIE y CORD (documentos/recibos — el
dominio más cercano a nuestras actas), IAM (manuscrito), PubTabNet/FinTabNet
(tablas). SROIE aparece en DTrOCR y OmniParser: es el puente natural entre
ambos.

**Métricas comunes:** mAP/AP y FPS (detección — RT-DETR), CER/WER y word
accuracy (reconocimiento — DTrOCR), F1 por campo y TEDS (extracción
estructurada — OmniParser). Son exactamente las métricas declaradas en nuestra
propuesta: mAP/Precision/Recall para la etapa 3 y CER/WER + exactitud por campo
para las etapas 4–5.

**Cómo sustentan nuestras decisiones:**
1. RT-DETR legitima incluir un DETR junto a YOLOv11 como candidato de detección
   y nos da la metodología de comparación justa (latencia end-to-end).
2. DTrOCR justifica preferir reconocedores Transformer con LM preentrenado
   (familia TrOCR) para el manuscrito, y su ablación de datos reales respalda
   nuestra decisión de anotar actas para fine-tuning.
3. OmniParser valida nuestra salida JSON estructurada, nos da la vara para el
   candidato Donut (que colapsa en tablas largas) y plantea la comparación
   pipeline modular vs end-to-end que haremos en la evaluación.

**Brecha que nuestro proyecto cubre:** ninguno de los tres evalúa dígitos
manuscritos en español sobre documentos oficiales con sellos y firmas — esa
combinación (actas de escrutinio ONPE) es la contribución empírica del grupo.

## Referencias (APA 7)

- Fujitake, M. (2024). DTrOCR: Decoder-only Transformer for optical character recognition. En *Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)* (pp. 8025–8035). IEEE/CVF.
- Wan, J., Song, S., Yu, W., Liu, Y., Cheng, W., Huang, F., Bai, X., Yao, C., & Yang, Z. (2024). OmniParser: A unified framework for text spotting, key information extraction and table recognition. En *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 15641–15653). IEEE/CVF.
- Zhao, Y., Lv, W., Xu, S., Wei, J., Wang, G., Dang, Q., Liu, Y., & Chen, J. (2024). DETRs beat YOLOs on real-time object detection. En *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 16965–16974). IEEE.
