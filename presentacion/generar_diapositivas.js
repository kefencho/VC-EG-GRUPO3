// Diapositivas del trabajo final — Visión por Computador (Grupo 3)
// Exposición 6-ago-2026, 15 min + 5 de preguntas. Español, notas del expositor incluidas.
const pptx = new (require('pptxgenjs'))();
const path = require('path');

// Rutas relativas al repo para que corra en cualquier maquina:
//   node generar_diapositivas.js                 -> presentacion/Presentacion - Grupo 3.pptx
//   node generar_diapositivas.js "ruta/salida.pptx"  -> donde tu quieras
const REPO = path.resolve(__dirname, '..');
const FIG = (f) => path.join(REPO, 'poster', 'figuras', f);
const OUT = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(__dirname, 'Presentacion - Grupo 3.pptx');

pptx.layout = 'LAYOUT_WIDE';           // 13.3 x 7.5 in
pptx.author = 'Grupo 3 — Maestría en IA, UNI';
pptx.title = 'Extracción automática de resultados electorales en actas ONPE 2026';

// --- paleta: azul institucional + rojo peruano + verde de hallazgo ---
const AZUL = '0F2E52', ROJO = 'C8102E', VERDE = '1B7F5A';
const GRIS = 'F4F6F9', BORDE = 'D3DAE4', TEXTO = '1F2A37', SUAVE = '5A6B7F';
const TIT = 'Cambria', CUERPO = 'Calibri';

const M = 0.6;                          // margen izquierdo
const W = 13.33 - 2 * M;                // ancho útil

function titulo(s, txt, sub) {
  s.addText(txt, {
    x: M, y: 0.34, w: W, h: 0.72, fontSize: 32, bold: true,
    color: AZUL, fontFace: TIT, margin: 0, valign: 'middle'
  });
  if (sub) {
    s.addText(sub, {
      x: M, y: 1.04, w: W, h: 0.36, fontSize: 15, color: SUAVE,
      fontFace: CUERPO, margin: 0, italic: true, valign: 'middle'
    });
  }
}

function tarjeta(s, x, y, w, h, relleno) {
  s.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: relleno || GRIS }, line: { color: BORDE, width: 1 }
  });
}

function cifra(s, x, y, w, valor, etiqueta, color) {
  s.addText(valor, {
    x, y, w, h: 0.85, fontSize: 46, bold: true, color, fontFace: TIT,
    align: 'center', margin: 0, valign: 'middle'
  });
  s.addText(etiqueta, {
    x, y: y + 0.85, w, h: 0.75, fontSize: 12.5, color: TEXTO,
    fontFace: CUERPO, align: 'center', margin: 0, valign: 'top'
  });
}

function lista(s, x, y, w, h, items, tam) {
  s.addText(items.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i !== items.length - 1 }
  })), {
    x, y, w, h, fontSize: tam || 14.5, color: TEXTO, fontFace: CUERPO,
    margin: 0, paraSpaceAfter: 8, valign: 'top'
  });
}

// =====================================================================
// 1. PORTADA
// =====================================================================
let s = pptx.addSlide();
s.background = { color: AZUL };
s.addShape(pptx.ShapeType.ellipse, { x: M - 0.13, y: 0.37, w: 1.51, h: 1.51, fill: { color: 'FFFFFF' }, line: { color: 'FFFFFF' } });
s.addImage({ path: FIG('logo_uni.png'), x: M, y: 0.5, w: 1.25, h: 1.25 });
s.addText('Extracción automática de resultados electorales\nen actas de escrutinio de la ONPE 2026', {
  x: M, y: 2.05, w: W, h: 1.5, fontSize: 36, bold: true, color: 'FFFFFF',
  fontFace: TIT, margin: 0, lineSpacingMultiple: 1.1
});
s.addText('Detección de regiones y reconocimiento de dígitos manuscritos sobre documentos oficiales', {
  x: M, y: 3.6, w: W, h: 0.4, fontSize: 17, color: 'CADCFC', fontFace: CUERPO, margin: 0, italic: true
});
s.addShape(pptx.ShapeType.rect, { x: M, y: 4.25, w: 2.2, h: 0.035, fill: { color: ROJO }, line: { color: ROJO } });
s.addText('Josemanuel Rossy Cañari Palante   ·   Kenny Asto Hinostroza   ·   Melissa Dessire Aylas Barranca   ·   Carlos Pérez Pérez', {
  x: M, y: 4.6, w: W, h: 0.4, fontSize: 15, color: 'FFFFFF', fontFace: CUERPO, margin: 0
});
s.addText('Maestría en Inteligencia Artificial — Visión por Computador · Grupo 3, Sección B\nUniversidad Nacional de Ingeniería · Prof. Elian Raquel Laura Riveros · 6 de agosto de 2026', {
  x: M, y: 5.1, w: W, h: 0.8, fontSize: 13, color: 'A9BDD6', fontFace: CUERPO, margin: 0, lineSpacingMultiple: 1.2
});
s.addImage({ path: FIG('qr_repo.png'), x: 11.55, y: 5.15, w: 1.15, h: 1.15 });
s.addText('código y datos', { x: 11.35, y: 6.32, w: 1.55, h: 0.25, fontSize: 10, color: 'A9BDD6', fontFace: CUERPO, align: 'center', margin: 0 });
s.addNotes('Buenos días. Somos el Grupo 3. Nuestro trabajo convierte en datos estructurados las actas de escrutinio que la ONPE publica como imágenes. En 15 minutos voy a cubrir: el problema, el dataset y cómo conseguimos ground truth sin anotar nada a mano, el pipeline de visión, el setup experimental, los resultados con intervalos de confianza, y las limitaciones. Todo el código y la evidencia por campo están en el repositorio del QR.');

// =====================================================================
// 2. PROBLEMA
// =====================================================================
s = pptx.addSlide();
titulo(s, '1. El problema', 'Los resultados oficiales existen, pero en formato visual');
s.addText([
  { text: 'La ONPE publica ', options: {} },
  { text: 'todas', options: { bold: true } },
  { text: ' las actas de escrutinio en formato digital, pero la información que llevan es ', options: {} },
  { text: 'visual', options: { bold: true, color: ROJO } },
  { text: ': un formulario escaneado donde los miembros de mesa escribieron los votos a mano.', options: {} }
], { x: M, y: 1.65, w: 6.9, h: 1.2, fontSize: 16, color: TEXTO, fontFace: CUERPO, margin: 0, lineSpacingMultiple: 1.15 });
lista(s, M, 2.95, 6.9, 2.6, [
  'La extracción manual no escala a ~88,000 mesas de una elección general.',
  'Sin datos estructurados no hay auditoría automática ni verificación independiente.',
  'Las imágenes traen ruido real: sellos, firmas, inclinación, bandas negras del escáner.'
], 15);
s.addText('¿Hasta dónde llega un pipeline clásico de visión por computador sobre actas reales muestreadas a escala nacional?', {
  x: M, y: 5.75, w: 6.9, h: 0.9, fontSize: 15, bold: true, color: AZUL, fontFace: CUERPO,
  margin: 0, italic: true, valign: 'middle'
});
tarjeta(s, 7.9, 1.65, 4.83, 4.9);
cifra(s, 8.1, 2.0, 4.43, '~88,000', 'mesas de sufragio en una elección general', ROJO);
cifra(s, 8.1, 3.6, 4.43, '46', 'campos por acta que hay que leer (38 organizaciones políticas + resúmenes)', AZUL);
cifra(s, 8.1, 5.2, 4.43, '0', 'datasets públicos de dígitos manuscritos en actas peruanas', SUAVE);
s.addNotes('El punto clave: el dato oficial existe pero está encerrado en una imagen. Nadie puede auditar 88 mil mesas a mano. Y no existe un dataset previo de este tipo de documento en español, con sellos y firmas encima: esa es la brecha que encontramos en el Related Work.');

// =====================================================================
// 3. APORTES
// =====================================================================
s = pptx.addSlide();
titulo(s, 'Qué aporta el trabajo', 'Cuatro contribuciones, todas verificables en el repositorio');
const aportes = [
  ['1', 'Evaluación sin anotación manual', 'El mismo portal publica los votos digitados oficialmente: cada acta descargada da ~43 pares campo–valor gratis.', AZUL],
  ['2', 'Detección robusta por registro fiducial', 'La plantilla fija se rompe con escaneos reales; alinear por las marcas de registro del formulario vale +8.7 puntos.', ROJO],
  ['3', 'Hallazgo poblacional con consecuencia de diseño', '24% de las actas son nacidas digitales: se parsean por capa de texto al 95.1%, sin visión.', VERDE],
  ['4', 'Techo cuantificado del OCR genérico', '59.6% con IC 95% [56.6, 62.5]: lo que se puede esperar sin entrenar, y por qué hace falta fine-tuning.', AZUL]
];
aportes.forEach((a, i) => {
  const x = M + (i % 2) * 6.35, y = 1.7 + Math.floor(i / 2) * 2.45;
  tarjeta(s, x, y, 6.0, 2.15);
  s.addShape(pptx.ShapeType.ellipse, { x: x + 0.28, y: y + 0.32, w: 0.62, h: 0.62, fill: { color: a[3] }, line: { color: a[3] } });
  s.addText(a[0], { x: x + 0.28, y: y + 0.32, w: 0.62, h: 0.62, fontSize: 20, bold: true, color: 'FFFFFF', fontFace: TIT, align: 'center', valign: 'middle', margin: 0 });
  s.addText(a[1], { x: x + 1.1, y: y + 0.28, w: 4.65, h: 0.6, fontSize: 15.5, bold: true, color: AZUL, fontFace: CUERPO, margin: 0, valign: 'middle' });
  s.addText(a[2], { x: x + 1.1, y: y + 0.92, w: 4.65, h: 1.0, fontSize: 12.5, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'top' });
});
s.addNotes('Estas cuatro contribuciones son las que defendemos. La primera es metodológica y es la que hace todo lo demás reproducible: no anotamos ni un campo a mano. La segunda es la corrección técnica que más impacto tuvo. La tercera cambió la arquitectura del sistema. La cuarta es el resultado honesto: 59.6% es un techo, no un producto.');

// =====================================================================
// 4. DATASET Y GROUND TRUTH
// =====================================================================
s = pptx.addSlide();
titulo(s, '2. Dataset y ground truth', 'Elecciones Generales del Perú 2026, primera vuelta (presidencial)');
const filas = [
  ['Fuente', 'Portal oficial de resultados de la ONPE. Descarga automatizada por su propia API (curl_cffi con huella de Chrome: el WAF rechaza un cliente HTTP común).'],
  ['Muestreo', 'Muestra aleatoria simple sin reemplazo sobre ~88,064 mesas, con semilla publicada (2026): 100 actas, 100% de éxito, 23 códigos departamentales, proporcional al tamaño (Lima 36%).'],
  ['Ground truth', 'El portal publica los conteos oficialmente digitados de cada mesa. Los usamos como verdad de terreno: ~43 pares campo–valor por acta, a costo cero de anotación.']
];
filas.forEach((f, i) => {
  const y = 1.68 + i * 1.42;
  tarjeta(s, M, y, 8.6, 1.25);
  s.addText(f[0], { x: M + 0.25, y: y + 0.12, w: 2.0, h: 0.35, fontSize: 15, bold: true, color: ROJO, fontFace: CUERPO, margin: 0 });
  s.addText(f[1], { x: M + 0.25, y: y + 0.47, w: 8.1, h: 0.7, fontSize: 12.5, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'top' });
});
tarjeta(s, 9.5, 1.68, 3.23, 4.16, AZUL);
s.addText('0', { x: 9.6, y: 2.15, w: 3.03, h: 1.0, fontSize: 60, bold: true, color: 'FFFFFF', fontFace: TIT, align: 'center', margin: 0, valign: 'middle' });
s.addText('campos anotados\na mano', { x: 9.6, y: 3.15, w: 3.03, h: 0.7, fontSize: 15, bold: true, color: 'FFFFFF', fontFace: CUERPO, align: 'center', margin: 0 });
s.addText('La evaluación es reproducible por cualquiera: basta la semilla y la API pública.', { x: 9.75, y: 4.0, w: 2.73, h: 1.6, fontSize: 12.5, color: 'CADCFC', fontFace: CUERPO, align: 'center', margin: 0, valign: 'top' });
s.addText('El piloto inicial usó mesas secuenciales de un solo distrito; el muestreo nacional corrige ese sesgo y es el que sustenta las cifras del paper.', {
  x: M, y: 6.0, w: 8.6, h: 0.6, fontSize: 12.5, color: SUAVE, fontFace: CUERPO, margin: 0, italic: true
});
s.addNotes('Este es el corazón metodológico. Dos decisiones: primero, el ground truth sale del mismo portal, así que cada acta trae 43 etiquetas gratis y no hay sesgo de anotador. Segundo, la muestra es aleatoria nacional con semilla publicada, no las primeras actas que encontramos. Si alguien corre el script con semilla 2026 obtiene exactamente las mismas 100 actas.');

// =====================================================================
// 5. HALLAZGO POBLACIONAL
// =====================================================================
s = pptx.addSlide();
titulo(s, 'Hallazgo: la población de actas es mixta', 'Clasificar el tipo de documento ANTES de procesar cambia la arquitectura');
s.addChart(pptx.ChartType.doughnut, [{
  name: 'Tipo de acta', labels: ['Manuscritas (escaneo)', 'Nacidas digitales (STAE)'], values: [76, 24]
}], {
  x: 0.5, y: 1.7, w: 5.1, h: 4.5, chartColors: [AZUL, VERDE], holeSize: 52,
  showLegend: true, legendPos: 'b', legendFontSize: 13, legendFontFace: CUERPO,
  showValue: true, dataLabelPosition: 'ctr', dataLabelColor: 'FFFFFF',
  dataLabelFontSize: 15, dataLabelFontBold: true, showTitle: false
});
lista(s, 6.0, 1.85, 6.75, 2.6, [
  '76 actas manuscritas: escaneo de una página, capa de texto vacía → requieren visión.',
  '24 actas STAE: dos páginas, firmadas digitalmente, votos tipografiados y capa de texto extraíble → se parsean directamente.',
  'Prevalencia del 24% con IC 95% de Wilson [16.7, 33.2]: alcanza para afirmar que la población es mixta, no para fijar la proporción exacta.'
], 14);
tarjeta(s, 6.0, 4.65, 6.75, 1.75, GRIS);
s.addText('95.1%', { x: 6.25, y: 4.85, w: 1.9, h: 0.8, fontSize: 38, bold: true, color: VERDE, fontFace: TIT, align: 'center', margin: 0, valign: 'middle' });
s.addText('de exactitud en las STAE parseando la capa de texto, sin visión alguna. Frente al 59.6% de la ruta manuscrita: enrutar por tipo de documento vale 35.5 puntos (IC 95% [32.6, 38.5]).', {
  x: 8.25, y: 4.85, w: 4.3, h: 1.35, fontSize: 12.5, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'middle'
});
s.addNotes('Este hallazgo no lo buscábamos: apareció al muestrear a nivel nacional. Una de cada cuatro actas ya es un PDF digital. Si tratáramos todo como imagen estaríamos haciendo OCR sobre documentos que se leen perfecto con un parser de texto. La consecuencia de diseño es concreta: el sistema debe clasificar el tipo de acta primero y enrutar.');

// =====================================================================
// 6. PIPELINE
// =====================================================================
s = pptx.addSlide();
titulo(s, '3. Metodología: pipeline de cinco etapas', 'Modular y auditable: cada etapa se evalúa y se puede apagar');
const etapas = [
  ['1', 'Adquisición', 'API ONPE\nPDF → PNG 300 dpi'],
  ['2', 'Preprocesamiento', 'Deskew, CLAHE,\ndenoise'],
  ['3', 'Detección', 'Plantilla registrada\npor fiduciales'],
  ['4', 'Reconocimiento', 'EasyOCR restringido\na dígitos'],
  ['5', 'Estructuración', 'JSON por acta\n+ evaluación']
];
etapas.forEach((e, i) => {
  const x = M + i * 2.48;
  s.addShape(pptx.ShapeType.roundRect, { x, y: 1.85, w: 2.2, h: 1.95, rectRadius: 0.1, fill: { color: i === 2 || i === 3 ? AZUL : GRIS }, line: { color: i === 2 || i === 3 ? AZUL : BORDE, width: 1 } });
  s.addText(e[0], { x: x + 0.12, y: 1.97, w: 0.45, h: 0.4, fontSize: 15, bold: true, color: i === 2 || i === 3 ? 'CADCFC' : ROJO, fontFace: TIT, margin: 0 });
  s.addText(e[1], { x: x + 0.15, y: 2.4, w: 1.9, h: 0.4, fontSize: 14.5, bold: true, color: i === 2 || i === 3 ? 'FFFFFF' : AZUL, fontFace: CUERPO, margin: 0 });
  s.addText(e[2], { x: x + 0.15, y: 2.82, w: 1.9, h: 0.85, fontSize: 11.5, color: i === 2 || i === 3 ? 'CADCFC' : SUAVE, fontFace: CUERPO, margin: 0, valign: 'top' });
  if (i < 4) s.addText('→', { x: x + 2.16, y: 2.55, w: 0.36, h: 0.4, fontSize: 20, bold: true, color: AZUL, align: 'center', margin: 0 });
});
s.addText('Las etapas 3 y 4 son el núcleo de visión y donde se concentran las decisiones que defendemos', {
  x: M, y: 3.95, w: W, h: 0.35, fontSize: 12.5, color: SUAVE, fontFace: CUERPO, italic: true, margin: 0
});
tarjeta(s, M, 4.5, 6.0, 2.0);
s.addText('¿Por qué no un detector aprendido (YOLO/RT-DETR)?', { x: M + 0.25, y: 4.65, w: 5.5, h: 0.4, fontSize: 14.5, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
s.addText('Porque no había etiquetas. El acta es un formulario de layout fijo con marcas de registro impresas: la plantilla registrada resuelve la localización HOY y además autogenera las etiquetas para entrenar el detector después.', {
  x: M + 0.25, y: 5.05, w: 5.5, h: 1.3, fontSize: 12.5, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'top'
});
tarjeta(s, 6.9, 4.5, 5.83, 2.0);
s.addText('¿Por qué OCR restringido a dígitos?', { x: 7.15, y: 4.65, w: 5.3, h: 0.4, fontSize: 14.5, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
s.addText('Los campos son enteros de 1 a 3 cifras. Restringir el alfabeto a 0–9 elimina de raíz las confusiones con letras y con los trazos de sellos y firmas que invaden la celda.', {
  x: 7.15, y: 5.05, w: 5.3, h: 1.3, fontSize: 12.5, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'top'
});
s.addNotes('Quiero anticipar la pregunta obvia: por qué no YOLO. La respuesta es que el detector aprendido necesita etiquetas y no las teníamos; y el documento es un formulario de layout fijo, así que la plantilla es la solución correcta para esta etapa. Además la plantilla registrada nos deja las etiquetas listas para entrenar YOLOv11 después: ese es el trabajo futuro, no un pendiente que se nos olvidó.');

// =====================================================================
// 7. DETECCIÓN
// =====================================================================
s = pptx.addSlide();
titulo(s, 'Etapa 3 — Detección: plantilla + registro fiducial', 'La corrección técnica de mayor impacto del proyecto');
s.addImage({ path: FIG('plantilla_overlay.png'), x: M, y: 1.7, w: 3.35, h: 4.74 });
s.addText('46 regiones proyectadas sobre un acta real después del registro', { x: M, y: 6.48, w: 3.35, h: 0.35, fontSize: 10.5, color: SUAVE, fontFace: CUERPO, align: 'center', margin: 0 });
lista(s, 4.35, 1.75, 8.4, 2.5, [
  'El acta es un formulario de layout fijo: 46 regiones definidas como fracciones de página (38 filas de organizaciones + 4 de resumen + 4 campos de contexto), calibradas sobre la mesa 000001.',
  'Problema encontrado en la muestra nacional: los escaneos traen bandas negras y desplazamientos de encuadre (mesa 084786 corrida ~184 px). Con fracciones fijas, el recorte cae en la fila equivocada y el acta se pierde entera.',
  'Solución: el propio formulario trae 15 cuadrados de registro impresos. Se detectan, se emparejan con la referencia por RANSAC de traslación (robusto a marcas faltantes y a falsos positivos) y se aplica una transformación afín parcial antes de recortar.'
], 13.5);
tarjeta(s, 4.35, 4.5, 4.05, 1.95);
cifra(s, 4.45, 4.72, 3.85, '+8.7 pp', 'de exactitud aporta el registro fiducial sobre la plantilla fija', ROJO);
tarjeta(s, 8.7, 4.5, 4.05, 1.95);
cifra(s, 8.8, 4.72, 3.85, '14% → 30%', 'mejora del acta peor del muestreo: deja de ser un fracaso total', AZUL);
s.addNotes('Este es el hallazgo técnico del que estamos más orgullosos. La plantilla fija funcionaba bien en el piloto de un distrito y se rompió al salir a nivel nacional, porque los escáneres de cada ODPE encuadran distinto. En vez de abandonar la plantilla, usamos algo que ya está impreso en el formulario: las marcas de registro. RANSAC porque algunas marcas faltan o el escáner mete falsos positivos, como los dígitos de muestra 0123456789 del margen.');

// =====================================================================
// 8. RECONOCIMIENTO
// =====================================================================
s = pptx.addSlide();
titulo(s, 'Etapa 4 — Reconocimiento y regla de dominio', 'Limpiar la celda importa tanto como el motor de OCR');
s.addImage({ path: FIG('limpieza_celdas.png'), x: 10.6, y: 1.72, w: 2.13, h: 4.9 });
s.addText('Recorte crudo → tinta aislada → separadores borrados', { x: 9.6, y: 6.65, w: 3.13, h: 0.3, fontSize: 10, color: SUAVE, fontFace: CUERPO, align: 'center', margin: 0 });
lista(s, M, 1.75, 9.6, 2.9, [
  'Margen interior: elimina el borde impreso de la casilla, que el OCR leía como un 1 o un 7.',
  'Aislamiento de tinta: umbral oscuro + Otsu para separar el trazo del fondo grisáceo del escaneo.',
  'Borrado de separadores punteados: son oscuros, así que ningún umbral los quita. Se borran por posición de plantilla (fracciones 0.31 y 0.70 del ancho de la celda). Sin esto, un 18 se leía 418 y un 22 se leía 212.',
  'Filtro de motas: descarta componentes conexos demasiado pequeños para ser un dígito.'
], 14);
tarjeta(s, M, 3.9, 9.6, 1.95, GRIS);
s.addText('Regla de dominio: celda vacía = 0 votos', { x: M + 0.28, y: 4.05, w: 9.0, h: 0.4, fontSize: 15.5, bold: true, color: ROJO, fontFace: CUERPO, margin: 0 });
s.addText('Los miembros de mesa dejan la casilla EN BLANCO en vez de escribir 0. No es un error de visión sino una convención del documento: separarla del desempeño del sistema evita atribuirle a la visión un problema que no es suyo. Vale +21.6 puntos a nivel nacional, y por eso reportamos SIEMPRE las dos cifras, con y sin regla.', {
  x: M + 0.28, y: 4.47, w: 9.0, h: 1.25, fontSize: 13, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'top'
});
s.addText('Qué errores quedan después de todo esto', { x: M, y: 6.05, w: 9.6, h: 0.32, fontSize: 13.5, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
s.addText('Dígitos delgados aislados que el detector del motor OCR no encuentra  ·  trazos que invaden la franja borrada del separador  ·  confusiones de forma (8↔18, 7↔9) en caligrafías anchas  ·  campos de casillas múltiples. Son errores de reconocimiento, no de localización.', {
  x: M, y: 6.38, w: 9.6, h: 0.75, fontSize: 12, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'top'
});
s.addNotes('Dos cosas para defender aquí. Primera: la mayor parte del trabajo de reconocimiento no está en el motor de OCR sino en limpiar la celda; los separadores punteados fueron la fuente número uno de errores. Segunda, y es una decisión que puede ser cuestionada: la regla de que una celda vacía vale cero. La reportamos SIEMPRE por separado, con y sin regla, justamente para que se vea cuánto es visión y cuánto es semántica del documento.');

// =====================================================================
// 9. SETUP EXPERIMENTAL
// =====================================================================
s = pptx.addSlide();
titulo(s, '4. Setup experimental', 'Cómo medimos, y por qué el intervalo de confianza es más ancho de lo que parecería');
tarjeta(s, M, 1.7, 6.05, 2.15);
s.addText('Métricas', { x: M + 0.25, y: 1.85, w: 5.5, h: 0.4, fontSize: 16, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
lista(s, M + 0.25, 2.28, 5.55, 1.45, [
  'Exactitud por campo: coincidencia exacta con el entero oficial.',
  'CER: tasa de error de caracteres sobre la cadena de dígitos.'
], 13);
tarjeta(s, 6.9, 1.7, 5.83, 2.15);
s.addText('Ablaciones', { x: 7.15, y: 1.85, w: 5.3, h: 0.4, fontSize: 16, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
s.addText('Cada componente se apaga y se vuelve a evaluar sobre las MISMAS salidas guardadas, sin re-correr el OCR. Cualquiera puede recalcular nuestras tablas con evaluar_salidas.py en segundos.', {
  x: 7.15, y: 2.28, w: 5.3, h: 1.4, fontSize: 13, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'top'
});
tarjeta(s, M, 4.05, 12.13, 2.5, AZUL);
s.addText('La unidad estadística es el ACTA, no el campo', { x: M + 0.3, y: 4.22, w: 11.5, h: 0.42, fontSize: 17, bold: true, color: 'FFFFFF', fontFace: CUERPO, margin: 0 });
s.addText('Los ~43 campos de un acta comparten escribano, escáner y calidad de impresión: no son observaciones independientes. Por eso todos los intervalos salen de un bootstrap agrupado por acta (10,000 réplicas de actas completas). Reportar un intervalo binomial por campo sería optimista: el efecto de diseño medido es 3.07, es decir, nuestras 76 actas equivalen a unos 1,066 campos independientes y no a 3,268.', {
  x: M + 0.3, y: 4.72, w: 11.5, h: 1.6, fontSize: 13.5, color: 'CADCFC', fontFace: CUERPO, margin: 0, valign: 'top', lineSpacingMultiple: 1.1
});
s.addNotes('Si me tuvieran que preguntar una sola cosa metodológica, es esta. Es muy fácil reportar 3,268 campos y sacar un intervalo binomial de más o menos 1.7 puntos. Sería falso: los campos de una misma acta están correlacionados. Agrupando por acta el intervalo real es de más o menos 2.9 puntos. Preferimos el número honesto.');

// =====================================================================
// 10. RESULTADO PRINCIPAL
// =====================================================================
s = pptx.addSlide();
titulo(s, '5. Resultado principal — muestra nacional', '76 actas manuscritas · 3,268 campos · bootstrap agrupado, 10,000 réplicas');
s.addChart(pptx.ChartType.bar, [{
  name: 'Exactitud por campo (%)',
  labels: ['Plantilla fija\nOCR crudo', 'Plantilla fija\n+ regla cero', 'Registrada\nOCR crudo', 'Registrada\n+ regla cero'],
  values: [26.81, 50.86, 38.00, 59.58]
}], {
  x: 0.45, y: 1.75, w: 7.6, h: 4.6, barDir: 'col', chartColors: [SUAVE, SUAVE, SUAVE, ROJO],
  showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 13, dataLabelFontBold: true,
  dataLabelColor: TEXTO, dataLabelFormatCode: '0.0"%"',
  valAxisMaxVal: 70, valAxisMinVal: 0, valAxisLabelColor: SUAVE, catAxisLabelColor: TEXTO,
  catAxisLabelFontSize: 11.5, valAxisLabelFontSize: 11, showLegend: false, showTitle: false,
  valGridLine: { color: 'E5E9EF', size: 1 }, catGridLine: { style: 'none' }
});
tarjeta(s, 8.35, 1.75, 4.4, 2.15, GRIS);
s.addText('59.58%', { x: 8.5, y: 1.95, w: 4.1, h: 0.85, fontSize: 44, bold: true, color: ROJO, fontFace: TIT, align: 'center', margin: 0, valign: 'middle' });
s.addText('IC 95% [56.61, 62.48]  ·  CER 0.401 [0.360, 0.444]', { x: 8.5, y: 2.85, w: 4.1, h: 0.9, fontSize: 13, color: TEXTO, fontFace: CUERPO, align: 'center', margin: 0, valign: 'top' });
lista(s, 8.35, 4.15, 4.4, 2.3, [
  'El registro fiducial aporta +8.7 pp.',
  'La regla vacío = 0 aporta +21.6 pp.',
  'Por acta: media 59.6%, sd 13 pp, rango 30–84%.',
  'La varianza que queda es caligrafía y calidad de escaneo, ya no desalineación.'
], 12.5);
s.addNotes('Este es el número que hay que recordar: 59.58% con un intervalo de 56.6 a 62.5. Las dos barras grises de la izquierda muestran de dónde venimos. Nótese que las dos mejoras son independientes y se suman: el registro arregla la localización, la regla arregla la semántica.');

// =====================================================================
// 11. PILOTO + ¿24 ACTAS ALCANZAN?
// =====================================================================
s = pptx.addSlide();
titulo(s, 'Ablación del piloto y precisión de cada submuestra', 'Cuánto aporta cada mejora, y cuántas actas hacen falta para afirmarlo');
s.addText('Piloto — 10 actas, 430 campos', { x: M, y: 1.7, w: 6.0, h: 0.35, fontSize: 15, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
s.addTable([
  [{ text: 'Configuración', options: { bold: true, color: 'FFFFFF', fill: { color: AZUL } } },
   { text: 'Exact.', options: { bold: true, color: 'FFFFFF', fill: { color: AZUL }, align: 'right' } },
   { text: 'CER', options: { bold: true, color: 'FFFFFF', fill: { color: AZUL }, align: 'right' } }],
  ['v1 · OCR de dígitos directo', { text: '43.95%', options: { align: 'right' } }, { text: '0.524', options: { align: 'right' } }],
  ['v2 · + aislamiento de tinta y bordes', { text: '52.09%', options: { align: 'right' } }, { text: '0.419', options: { align: 'right' } }],
  ['v3 · + borrado de separadores, Otsu', { text: '52.79%', options: { align: 'right' } }, { text: '0.476', options: { align: 'right' } }],
  [{ text: 'v4 · + regla celda vacía = 0', options: { bold: true } }, { text: '58.37%', options: { align: 'right', bold: true } }, { text: '0.420', options: { align: 'right', bold: true } }]
], { x: M, y: 2.1, w: 6.0, colW: [3.6, 1.2, 1.2], fontSize: 12, fontFace: CUERPO, color: TEXTO, border: { type: 'solid', color: BORDE, pt: 1 }, rowH: 0.34, valign: 'middle' });
s.addText('¿Y 24 actas alcanzan para afirmar el 95.1% de las STAE?', { x: 6.9, y: 1.7, w: 5.83, h: 0.35, fontSize: 15, bold: true, color: VERDE, fontFace: CUERPO, margin: 0 });
s.addTable([
  [{ text: 'Submuestra', options: { bold: true, color: 'FFFFFF', fill: { color: VERDE } } },
   { text: 'ICC', options: { bold: true, color: 'FFFFFF', fill: { color: VERDE }, align: 'right' } },
   { text: 'DEFF', options: { bold: true, color: 'FFFFFF', fill: { color: VERDE }, align: 'right' } },
   { text: 'IC 95%', options: { bold: true, color: 'FFFFFF', fill: { color: VERDE }, align: 'right' } }],
  ['STAE — 24 actas', { text: '~0', options: { align: 'right' } }, { text: '1.00', options: { align: 'right' } }, { text: '±0.58 pp', options: { align: 'right', bold: true } }],
  ['Manuscritas — 76 actas', { text: '0.049', options: { align: 'right' } }, { text: '3.07', options: { align: 'right' } }, { text: '±2.91 pp', options: { align: 'right', bold: true } }]
], { x: 6.9, y: 2.1, w: 5.83, colW: [2.33, 0.9, 0.9, 1.7], fontSize: 12, fontFace: CUERPO, color: TEXTO, border: { type: 'solid', color: BORDE, pt: 1 }, rowH: 0.34, valign: 'middle' });
tarjeta(s, 6.9, 3.35, 5.83, 3.0, GRIS);
s.addText('Sí, y por una razón medible.', { x: 7.15, y: 3.5, w: 5.3, h: 0.35, fontSize: 14.5, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
s.addText('El parseo de la capa de texto es determinista: la varianza entre actas cae por debajo de la binomial (ICC ≈ 0), así que 24 actas rinden como 1,004 observaciones independientes y el intervalo es ±0.58 puntos. En las manuscritas, en cambio, la caligrafía correlaciona los errores dentro de cada acta (DEFF 3.07) y las 76 actas solo dan ±2.91.\n\nLo que 24 actas NO sostienen con precisión es la prevalencia del 24%: ese estimador tiene IC de Wilson [16.7, 33.2] y por eso lo reportamos como tal.', {
  x: 7.15, y: 3.9, w: 5.3, h: 2.3, fontSize: 12, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'top', lineSpacingMultiple: 1.05
});
s.addText('El piloto (58.37%) quedó cerca del nacional (59.58%) por casualidad: solo la estimación nacional tiene margen de error válido y cobertura del país.', {
  x: M, y: 4.05, w: 6.0, h: 0.8, fontSize: 12, color: SUAVE, fontFace: CUERPO, margin: 0, italic: true, valign: 'top'
});
tarjeta(s, M, 4.95, 6.0, 1.9, GRIS);
s.addText('Por qué el piloto no bastaba', { x: M + 0.25, y: 5.1, w: 5.5, h: 0.35, fontSize: 14, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
lista(s, M + 0.25, 5.5, 5.5, 1.25, [
  'Mesas secuenciales de un solo distrito: mismo escáner, misma ODPE, misma caligrafía.',
  'Sin marco muestral no hay margen de error válido: el 58.37% no se puede extrapolar al país.'
], 11.5);
s.addNotes('Aquí anticipo la pregunta que casi seguro nos harán: 24 actas suenan pocas. La respuesta es que el tamaño necesario depende de cuánta varianza hay entre unidades, no del número en sí. En las STAE el proceso es determinista y con 24 actas el intervalo es de más o menos medio punto. Y somos explícitos en lo que 24 actas no sostienen: la proporción exacta de actas electrónicas.');

// =====================================================================
// 12. EXPERIMENTO LLM
// =====================================================================
s = pptx.addSlide();
titulo(s, '¿Y si le damos el acta completa a un LLM multimodal?', 'Experimento sugerido por la profesora, ejecutado y medido con el mismo protocolo');
tarjeta(s, M, 1.72, 5.9, 2.0);
s.addText('Diseño del experimento', { x: M + 0.25, y: 1.87, w: 5.4, h: 0.35, fontSize: 15, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
s.addText('Gemini 2.5 Flash recibe la imagen del acta completa más dos ejemplos resueltos (imagen + su JSON) y devuelve el JSON de votos. Sin plantilla, sin registro y sin motor de OCR. Mismas 15 actas manuscritas, 645 campos, misma métrica.', {
  x: M + 0.25, y: 2.25, w: 5.4, h: 1.4, fontSize: 12.5, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'top'
});
s.addTable([
  [{ text: 'Método', options: { bold: true, color: 'FFFFFF', fill: { color: AZUL } } },
   { text: 'Exactitud', options: { bold: true, color: 'FFFFFF', fill: { color: AZUL }, align: 'right' } },
   { text: 'CER', options: { bold: true, color: 'FFFFFF', fill: { color: AZUL }, align: 'right' } }],
  [{ text: 'Pipeline (plantilla registrada + OCR)', options: { bold: true } },
   { text: '60.93%', options: { align: 'right', bold: true, color: ROJO } },
   { text: '0.395', options: { align: 'right', bold: true } }],
  ['LLM few-shot, extremo a extremo', { text: '48.37%', options: { align: 'right' } }, { text: '0.591', options: { align: 'right' } }]
], { x: M, y: 3.95, w: 5.9, colW: [3.3, 1.3, 1.3], fontSize: 12.5, fontFace: CUERPO, color: TEXTO, border: { type: 'solid', color: BORDE, pt: 1 }, rowH: 0.38, valign: 'middle' });
s.addText('El pipeline especializado gana por 12.6 puntos', { x: M, y: 5.5, w: 5.9, h: 0.35, fontSize: 14, bold: true, color: ROJO, fontFace: CUERPO, margin: 0, align: 'center' });
tarjeta(s, 6.85, 1.72, 5.88, 4.75);
s.addText('Lectura crítica', { x: 7.1, y: 1.87, w: 5.4, h: 0.35, fontSize: 15, bold: true, color: AZUL, fontFace: CUERPO, margin: 0 });
lista(s, 7.1, 2.3, 5.4, 4.0, [
  'El LLM interpreta bien la estructura del formulario, pero no está entrenado para dígitos manuscritos peruanos. Coincide con DTrOCR: el reconocimiento fuerte de manuscrito viene del entrenamiento específico, no de la capacidad general.',
  'Se hunde en los escaneos malos: 20.9% y 23.3% en las dos peores actas, donde el pipeline aún lee 34.9% y 53.5%. El recorte le entrega al reconocedor una celda aislada; el LLM tiene que pelear con todo el ruido alrededor.',
  'Su ventaja es otra: cero ingeniería de detección. Sirve como pre-etiquetador para arrancar con un formulario nuevo, no como reemplazo del reconocedor.'
], 12.5);
s.addNotes('La profesora nos sugirió probar etiquetado few-shot con un LLM con visión. Lo hicimos y medimos con el mismo protocolo, y el resultado es contraintuitivo pero sólido: el pipeline clásico gana por 12.6 puntos. Esto no descarta al LLM: su valor está en arrancar sin anotación, y encaja perfecto en el plan de fine-tuning como pre-etiquetador que un humano corrige.');

// =====================================================================
// 13. LIMITACIONES
// =====================================================================
s = pptx.addSlide();
titulo(s, '6. Limitaciones y trabajo futuro', 'Lo que este número NO dice, y hacia dónde va el sistema');
const lims = [
  ['Límite', '59.6% es un techo del OCR genérico, no una exactitud desplegable. Un sistema de auditoría real necesita además una medida de confianza por campo para derivar a revisión humana.', ROJO],
  ['Alcance', 'Un solo proceso electoral y un solo formato de acta. La plantilla habría que recalibrarla para otra elección; el registro fiducial es lo que hace esa recalibración barata.', ROJO],
  ['Siguiente paso', 'Fine-tuning de TrOCR con los pares campo–valor gratuitos: ~43 por acta, ~43,000 con solo 1,000 actas descargadas. Los errores que quedan son de reconocimiento, no de localización: exactamente lo que el fine-tuning reemplaza.', VERDE],
  ['Siguiente paso', 'Entrenar YOLOv11 y RT-DETR con las etiquetas que la plantilla registrada autogenera, y comparar el pipeline modular contra parsers unificados tipo OmniParser o Donut.', VERDE]
];
lims.forEach((l, i) => {
  const y = 1.72 + i * 1.24;
  tarjeta(s, M, y, 12.13, 1.08);
  s.addShape(pptx.ShapeType.ellipse, { x: M + 0.22, y: y + 0.28, w: 0.52, h: 0.52, fill: { color: l[2] }, line: { color: l[2] } });
  s.addText(i < 2 ? '!' : '→', { x: M + 0.22, y: y + 0.28, w: 0.52, h: 0.52, fontSize: 17, bold: true, color: 'FFFFFF', fontFace: TIT, align: 'center', valign: 'middle', margin: 0 });
  s.addText(l[0], { x: M + 0.95, y: y + 0.15, w: 1.9, h: 0.35, fontSize: 13.5, bold: true, color: l[2], fontFace: CUERPO, margin: 0 });
  s.addText(l[1], { x: M + 2.85, y: y + 0.13, w: 9.05, h: 0.85, fontSize: 12.5, color: TEXTO, fontFace: CUERPO, margin: 0, valign: 'middle' });
});
s.addText('Todos los experimentos corren en una laptop con GPU de 4 GB: 10.8 s por acta con GPU frente a 57 s en CPU, con exactitud idéntica.', {
  x: M, y: 6.72, w: 12.13, h: 0.4, fontSize: 12, color: SUAVE, fontFace: CUERPO, italic: true, margin: 0
});
s.addNotes('Ser explícitos con las limitaciones es parte de la defensa. 59.6% no es un producto: es la medición honesta del techo de un OCR genérico sobre este documento. Y lo importante es que ya sabemos dónde está el cuello de botella: los errores que quedan son de reconocimiento, no de localización, y para eso ya tenemos 43 mil etiquetas gratis esperando.');

// =====================================================================
// 14. CIERRE
// =====================================================================
s = pptx.addSlide();
s.background = { color: AZUL };
s.addText('Cuatro lecciones que se llevan a cualquier documento oficial', {
  x: M, y: 0.75, w: W, h: 0.7, fontSize: 30, bold: true, color: 'FFFFFF', fontFace: TIT, margin: 0
});
const lecc = [
  ['1', 'Registrar la plantilla sobre las marcas fiduciales del formulario antes de cualquier recorte por coordenadas fijas.'],
  ['2', 'Separar la semántica de dominio (casilla en blanco = 0) del desempeño de visión: mezclarlas oculta dónde falla el sistema.'],
  ['3', 'Clasificar el tipo de documento primero: enrutar las actas nacidas digitales vale 35.5 puntos.'],
  ['4', 'La generalidad todavía no le gana a la especialización: el LLM multimodal es más barato de construir y 12.6 puntos menos exacto.']
];
lecc.forEach((l, i) => {
  const y = 1.75 + i * 1.02;
  s.addShape(pptx.ShapeType.ellipse, { x: M, y: y + 0.06, w: 0.55, h: 0.55, fill: { color: ROJO }, line: { color: ROJO } });
  s.addText(l[0], { x: M, y: y + 0.06, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: 'FFFFFF', fontFace: TIT, align: 'center', valign: 'middle', margin: 0 });
  s.addText(l[1], { x: M + 0.8, y, w: 10.0, h: 0.75, fontSize: 15, color: 'FFFFFF', fontFace: CUERPO, margin: 0, valign: 'middle' });
});
s.addImage({ path: FIG('qr_repo.png'), x: 11.25, y: 2.05, w: 1.5, h: 1.5 });
s.addText('github.com/\ncarlosperez100/\nonpe_actas', { x: 10.9, y: 3.6, w: 2.2, h: 0.8, fontSize: 10.5, color: 'CADCFC', fontFace: CUERPO, align: 'center', margin: 0 });
s.addText('Gracias. Quedamos atentos a sus preguntas.', {
  x: M, y: 6.15, w: 8.0, h: 0.5, fontSize: 18, bold: true, color: 'CADCFC', fontFace: TIT, margin: 0
});
s.addNotes('Cierro con las cuatro lecciones que creemos que valen más allá de este documento en particular. El código, la evidencia por campo y la semilla del muestreo están en el repositorio: cualquiera puede reproducir las cifras. Gracias.');

pptx.writeFile({ fileName: OUT }).then(() => console.log('OK ->', OUT));
