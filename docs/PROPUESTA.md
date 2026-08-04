# Propuesta de Proyecto — Presentación de Dataset

> Documento de la presentación de propuesta requerida por la docente
> (Project Proposal and Dataset Presentation). Resume el problema, objetivo,
> dataset, relevancia, limitaciones, enfoque, motivación y supuestos/riesgos.

## Problema
Las actas de escrutinio publican los resultados oficiales por mesa en formato
visual (PDF/imagen), lo que impide su procesamiento automático masivo. La
extracción manual es lenta, propensa a errores y difícil de auditar.

## Objetivo
Detectar y reconocer automáticamente los resultados electorales de las actas de
las Elecciones Generales del Perú 2026 mediante Visión por Computadora.

## Dataset
Actas de escrutinio de la ONPE 2026 – 1ª vuelta. Fuente: Portal de Resultados
de la ONPE (PDF/imagen). Recolección automatizada mediante el scraper del repo.
Características: número de mesa, resultados por organización política, votos
blancos/nulos/impugnados, totales, firmas de miembros de mesa.

## Relevancia
Regiones bien delimitadas (tabla, totales, firmas, observaciones) aptas para
detección; campos manuscritos aptos para reconocimiento. Aplicación real:
automatización documental electoral y apoyo a auditorías.

## Limitaciones y desafíos
Calidad de imagen variable, escritura manuscrita, ruido visual (sellos/firmas),
desbalance de clases, ausencia de anotaciones iniciales, múltiples formatos de acta.

## Enfoque propuesto
Pipeline de 5 etapas: entrada → preprocesamiento  →
reconocimiento (OCR) → datos estructurados (JSON). Métricas: mAP/Precision/Recall
para detección; CER/WER y exactitud por campo/documento para reconocimiento.

## Motivación
Académica (aplicar VC a un problema real), tecnológica (modelos sobre documentos
complejos) y social (transparencia y verificación electoral).

## Supuestos, riesgos y restricciones
- **Supuestos:** actas representativas, calidad suficiente, valores legibles.
- **Riesgos:** calidad insuficiente, errores en manuscrito, mucho etiquetado
  manual, hardware limitado.
- **Restricciones:** tiempo de entrenamiento, recursos computacionales,
  disponibilidad parcial del dataset.
