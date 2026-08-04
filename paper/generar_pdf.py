# -*- coding: utf-8 -*-
"""
Genera el PDF del paper en layout IEEE conference (2 columnas, Times, A4)
usando reportlab — para entrega inmediata sin compilador LaTeX local.
El fuente canónico para Overleaf/WVC es main.tex (mismo contenido).

Uso:  python generar_pdf.py   ->  ../\"Paper WVC - Grupo 3.pdf\"
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Image, Table, TableStyle, FrameBreak,
                                NextPageTemplate)

AQUI = Path(__file__).parent
SALIDA = AQUI.parent.parent / "Paper WVC - Grupo 3.pdf"

W, H = A4
MARGEN = 1.78 * cm          # ~0.7 in
SEP = 0.6 * cm              # separación entre columnas
COL_W = (W - 2 * MARGEN - SEP) / 2
ALTO_TITULO = 4.6 * cm

# ----------------------------------------------------------------- estilos
def st(nombre, **kw):
    base = dict(fontName="Times-Roman", fontSize=9.7, leading=11.6,
                alignment=TA_JUSTIFY, spaceAfter=3)
    base.update(kw)
    return ParagraphStyle(nombre, **base)

s_titulo = st("titulo", fontSize=20, leading=24, alignment=TA_CENTER,
              spaceAfter=10)
s_autores = st("autores", fontSize=10.5, leading=13, alignment=TA_CENTER)
s_afil = st("afil", fontSize=9.5, leading=12, alignment=TA_CENTER,
            spaceAfter=0)
s_abs = st("abs", fontName="Times-Bold", fontSize=9, leading=11)
s_kw = st("kw", fontName="Times-Italic", fontSize=9, leading=11, spaceAfter=8)
s_h1 = st("h1", fontSize=10, leading=13, alignment=TA_CENTER,
          spaceBefore=8, spaceAfter=4)
s_h2 = st("h2", fontName="Times-Italic", fontSize=10, leading=12,
          spaceBefore=6, spaceAfter=3, alignment=0)
s_cuerpo = st("cuerpo")
s_item = st("item", leftIndent=0.45 * cm, firstLineIndent=-0.25 * cm)
s_cap = st("cap", fontSize=8.6, leading=10.4, spaceBefore=3, spaceAfter=8)
s_ref = st("ref", fontSize=8.6, leading=10.4, leftIndent=0.5 * cm,
           firstLineIndent=-0.5 * cm, spaceAfter=2)

def H1(txt):
    return Paragraph(f"<b>{txt}</b>", s_h1)

def P(txt):
    return Paragraph(txt, s_cuerpo)

def figura(nombre, caption, escala=1.0):
    ruta = AQUI / "figuras" / nombre
    from PIL import Image as PILImage
    with PILImage.open(ruta) as im:
        iw, ih = im.size
    w = COL_W * escala
    return [Spacer(1, 4), Image(str(ruta), width=w, height=w * ih / iw),
            Paragraph(caption, s_cap)]

def tabla(titulo, filas, negrita_ultima=False):
    t = Table(filas, colWidths=[COL_W * 0.58, COL_W * 0.21, COL_W * 0.21])
    estilo = [
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]
    if negrita_ultima:
        estilo.append(("FONTNAME", (0, -1), (-1, -1), "Times-Bold"))
    t.setStyle(TableStyle(estilo))
    return [Spacer(1, 4), Paragraph(titulo, s_cap), t, Spacer(1, 6)]


# ----------------------------------------------------------------- documento
doc = BaseDocTemplate(str(SALIDA), pagesize=A4,
                      leftMargin=MARGEN, rightMargin=MARGEN,
                      topMargin=MARGEN, bottomMargin=MARGEN,
                      title="Automatic Extraction of Electoral Results from "
                            "the Tally Sheets of the 2026 Peruvian General Elections",
                      author="Grupo 3 - Vision por Computador")

y_cols_p1 = H - MARGEN - ALTO_TITULO
frame_titulo = Frame(MARGEN, y_cols_p1, W - 2 * MARGEN, ALTO_TITULO,
                     id="titulo", topPadding=0, bottomPadding=0)
col1_p1 = Frame(MARGEN, MARGEN, COL_W, y_cols_p1 - MARGEN, id="c1")
col2_p1 = Frame(MARGEN + COL_W + SEP, MARGEN, COL_W, y_cols_p1 - MARGEN, id="c2")
col1 = Frame(MARGEN, MARGEN, COL_W, H - 2 * MARGEN, id="d1")
col2 = Frame(MARGEN + COL_W + SEP, MARGEN, COL_W, H - 2 * MARGEN, id="d2")

doc.addPageTemplates([
    PageTemplate(id="Primera", frames=[frame_titulo, col1_p1, col2_p1]),
    PageTemplate(id="Resto", frames=[col1, col2]),
])

E = []
E.append(Paragraph("Automatic Extraction of Electoral Results from the Tally "
                   "Sheets of the 2026 Peruvian General Elections", s_titulo))
E.append(Paragraph("Josemanuel Rossy Cañari Palante, Kenny Asto Hinostroza, "
                   "Melissa Dessire Aylas Barranca, Carlos Pérez Pérez", s_autores))
E.append(Paragraph("Master's Program in Artificial Intelligence — Computer "
                   "Vision, Group 3 — Universidad Nacional de Ingeniería, Lima, Peru", s_afil))
E.append(NextPageTemplate("Resto"))
E.append(FrameBreak())

E.append(Paragraph(
    "<i>Abstract</i>—Official electoral results in Peru are published as "
    "scanned tally sheets (actas), which prevents large-scale automatic "
    "processing. We present an end-to-end pipeline that downloads actas from "
    "the official ONPE portal, locates 46 fields per document through a fixed "
    "template anchored by fiducial-mark registration, and reads handwritten "
    "vote counts with digit-restricted OCR. Two design choices make "
    "evaluation annotation-free and reproducible: ground truth comes from the "
    "officially digitized results published by the same portal, and the test "
    "set is a seeded random national sample (100 actas, 23 departments). The "
    "acta population is heterogeneous: 24% are born-digital documents "
    "whose text layer yields 95.1% field accuracy without any vision. On the "
    "76 scanned handwritten actas (3,268 fields), the pipeline attains 59.6% "
    "field accuracy (95% CI [56.6, 62.5]) and 0.401 CER, quantifying the "
    "ceiling of generic OCR and motivating fine-tuned recognizers trained on "
    "the ~43 field–value pairs each acta provides for free.", s_abs))
E.append(Paragraph("<b>Keywords</b>—document analysis, optical character "
                   "recognition, handwritten digit recognition, electoral "
                   "documents, template registration", s_kw))

E.append(H1("I. I<font size=8>NTRODUCTION</font>"))
E.append(P("Scrutiny tally sheets (<i>actas de escrutinio</i>) are the "
           "official source of electoral results for each polling station in "
           "Peru. Although the National Office of Electoral Processes (ONPE) "
           "publishes every acta digitally, the information they carry is "
           "visual: a scanned form where members of the polling station wrote "
           "vote counts by hand. Manual extraction is slow, error-prone and "
           "does not scale to the ~88,000 polling stations of a general "
           "election, which limits automatic auditing and independent "
           "verification."))
E.append(P("This work asks a concrete question: <i>how far can a classical "
           "computer vision pipeline go on real, nationally sampled Peruvian "
           "actas, and what does that imply for the design of a production "
           "system?</i> We build and evaluate a five-stage pipeline "
           "(acquisition, preprocessing, region detection, recognition, "
           "structured output) on the first round of the 2026 General "
           "Elections. Our contributions are:"))
E.append(Paragraph("1) <b>An annotation-free, reproducible evaluation "
                   "protocol.</b> The same portal that publishes each acta "
                   "image also publishes its officially digitized vote counts "
                   "through an internal API. We use those values as ground "
                   "truth, which turns every downloaded acta into ~43 labeled "
                   "field–value pairs at zero annotation cost, and we sample "
                   "the test set randomly at national scale with a published "
                   "seed.", s_item))
E.append(Paragraph("2) <b>Template detection made robust by fiducial "
                   "registration.</b> The acta is a fixed-layout form with "
                   "printed registration marks. We show that fixed fractional "
                   "templates break under real-world scanner framing (black "
                   "bands, offsets) and that a RANSAC-based translation "
                   "matching of fiducial marks followed by a partial affine "
                   "warp recovers alignment, adding +8.7 accuracy points.",
                   s_item))
E.append(Paragraph("3) <b>A population finding with architectural "
                   "consequences.</b> In a random national sample, 24% of "
                   "actas are born-digital (STAE) documents whose PDF text "
                   "layer can be parsed directly with 95.1% field accuracy; "
                   "only 76% are scanned handwritten forms that require "
                   "vision. A production system should classify the acta type "
                   "first and route accordingly.", s_item))
E.append(Paragraph("4) <b>A quantified ceiling for generic OCR.</b> On "
                   "handwritten actas, generic digit-restricted OCR with "
                   "careful cell cleaning reaches 59.6% field accuracy (95% "
                   "CI [56.6, 62.5], clustered bootstrap). This bounds what "
                   "can be expected without training and motivates "
                   "fine-tuning transformer recognizers with the free labels "
                   "described above.", s_item))

E.append(H1("II. R<font size=8>ELATED</font> W<font size=8>ORK</font>"))
E.append(P("<b>Real-time detection.</b> RT-DETR [1] showed that a carefully "
           "designed DETR outperforms comparable-scale YOLO detectors (L/X) in both "
           "accuracy and speed while removing non-maximum suppression (NMS) and its "
           "manually tuned thresholds. For tally sheets — tables of "
           "contiguous cells frequently overlapped by stamps and signatures — "
           "threshold-free, end-to-end detection is attractive, and RT-DETR's "
           "end-to-end latency protocol is the one we will adopt to compare "
           "learned detectors (YOLOv11 vs. RT-DETR) in future work. In this paper, "
           "detection is solved by template registration, which doubles as an "
           "automatic label generator for those detectors."))
E.append(P("<b>Text recognition.</b> TrOCR [4] established transformer "
           "encoder–decoder OCR with pre-trained language models, and DTrOCR "
           "[2] showed that a decoder-only generative architecture surpasses "
           "it on printed, scene and handwritten text (CER 2.38 on IAM "
           "without an external language model). These results justify "
           "transformer recognizers as the upgrade path for our "
           "handwritten-digit fields; a caveat for our setting is that "
           "language priors may “correct” digit strings toward "
           "plausible sequences, which matters when reading isolated numbers."))
E.append(P("<b>Unified document parsing.</b> OmniParser [3] unifies text "
           "spotting, key information extraction and table recognition "
           "through structured-point sequences, and highlights the weakness "
           "of monolithic sequence generation: Donut [5] collapses on long "
           "tables due to error accumulation, dropping to 22.7 TEDS on "
           "PubTabNet vs. 88.83 for OmniParser. An acta is "
           "precisely a long table plus key fields; OmniParser's explicit "
           "localization of every extracted value also matches the "
           "auditability requirement of electoral documents. We keep a "
           "modular pipeline — whose per-stage metrics are easier to diagnose "
           "— and treat unified end-to-end parsing as the alternative to "
           "compare against."))
E.append(P("None of these works evaluates handwritten digits in Spanish on "
           "official forms with stamps and signatures; that combination is "
           "the empirical gap this project addresses."))

E.append(H1("III. D<font size=8>ATASET</font>"))
E.append(Paragraph("<i>A. Source and acquisition</i>", s_h2))
E.append(P("All documents come from the official ONPE results portal for the "
           "2026 General Elections (first round, April 12, 2026). The portal "
           "exposes an internal API: searching for a polling station returns its "
           "actas and their processing statuses; the acta detail lists its files, where type 1 "
           "is the scrutiny sheet; a signed S3 URL serves the PDF. Downloads "
           "use browser TLS impersonation, a conservative request rate, and a "
           "resumable manifest."))
E.append(Paragraph("<i>B. Sampling design</i>", s_h2))
E.append(P("The universe holds ~88,064 station codes (upper bound located by "
           "exponential-plus-binary search against the API). We drew a simple "
           "random sample without replacement with a <b>published seed "
           "(2026)</b>: 100 actas, 100% hit rate, covering 23 of Peru's "
           "department-level ubigeo prefixes (the Peruvian standard geographic location code) with a size-proportional "
           "distribution (Lima concentrates 36%, consistent with its "
           "electorate share). This corrects the pilot bias of sequential "
           "station codes from a single district."))
E.append(Paragraph("<i>C. Population heterogeneity</i>", s_h2))
E.append(P("Classifying each PDF by page count and text layer reveals two "
           "document types: <b>76 handwritten actas</b> (single-page scans, "
           "empty text layer) and <b>24 born-digital STAE actas</b> (two-page "
           "digitally signed documents with typeset vote counts and an "
           "extractable text layer). All vision experiments run on the 76 "
           "handwritten actas; STAE actas are processed by direct text "
           "parsing (Sec. IV-E)."))
E.append(Paragraph("<i>D. Ground truth</i>", s_h2))
E.append(P("For every sampled station we store the officially digitized "
           "counts returned by the API: votes per political organization (38 "
           "rows), blank/null/challenged votes, totals and electorate. Form "
           "positions 04 and 14 correspond to withdrawn parties, are empty on "
           "the form and null in the API; they are excluded (a null-to-null "
           "match would spuriously inflate accuracy). This yields <b>43 "
           "evaluable fields per acta, 3,268 in total</b>."))

E.append(H1("IV. M<font size=8>ETHOD</font>"))
E.append(Paragraph("<i>A. Pipeline overview</i>", s_h2))
E.append(P("(1) <i>Acquisition</i>: PDF download plus official ground truth. "
           "(2) <i>Preprocessing</i>: 300 DPI rasterization, deskew by "
           "dominant angle, CLAHE contrast normalization, non-local-means "
           "denoising (OpenCV). (3) <i>Region detection</i>: template with "
           "fiducial registration (below). (4) <i>Recognition</i>: "
           "digit-restricted OCR on cleaned cells. (5) <i>Structured "
           "output</i>: one JSON per acta with the proposal's schema."))
E.append(Paragraph("<i>B. Template regions with fiducial registration</i>", s_h2))
E.append(P("The acta is a fixed-layout form, so 46 regions (38 vote cells "
           "arranged as equally spaced rows, four summary rows, station "
           "number, electorate, citizen total, observations) are defined once "
           "as page fractions calibrated on a reference acta (Fig. 1). "
           "National sampling exposed the failure mode of fixed fractions: "
           "scanner framing varies (black margin bands, content offsets of up to "
           "~184 px), shifting every cell one row off and producing CER > 1. "
           "The form itself provides the fix: printed black registration "
           "squares along the border. We detect them as dark, square, "
           "high-fill connected components inside border bands; match "
           "detected marks to 15 calibrated reference positions by "
           "translation RANSAC (each detected–reference pair proposes a "
           "shift, the shift with most inliers wins), robust to missing marks "
           "and to false positives such as the printed sample digits; and "
           "estimate a partial affine transform that warps the page to the "
           "reference frame before cropping."))
E.extend(figura("plantilla_overlay.png",
                "Fig. 1. Reference acta with the 46 template regions: 38 vote "
                "cells (blue), summary and header fields (red). Region "
                "coordinates are page fractions, applied after fiducial "
                "registration.", 0.96))
E.append(Paragraph("<i>C. Recognition of handwritten counts</i>", s_h2))
E.append(P("Cells are read with EasyOCR restricted to a digit vocabulary, "
           "after a cleaning cascade motivated by error analysis on a "
           "10-acta pilot (Fig. 2): (i) an interior margin removes printed "
           "cell borders, which were previously misread as extra digits; (ii) per-cell Otsu "
           "binarization isolates pen ink and survives the alternating shaded "
           "rows of the form; (iii) the dotted intra-cell separators — as "
           "dark as ink, hence immune to thresholding — are erased <i>by "
           "template position</i> (fixed fractions of the cell width); (iv) a "
           "connected-component speckle filter removes digitization noise; "
           "(v) fields with per-digit printed boxes (citizen total) are read "
           "box by box. A fallback re-reads the raw crop when cleaning "
           "empties faint strokes."))
E.extend(figura("limpieza_celdas.png",
                "Fig. 2. Ink isolation on problem cells (top: crop; bottom: "
                "cleaned). Dotted separators and printed borders — previously "
                "read as digits (e.g. 18 read as 418) — are removed by "
                "threshold, template-positioned erasure and speckle "
                "filtering.", 0.9))
E.append(Paragraph("<i>D. Domain rule: empty cell means zero</i>", s_h2))
E.append(P("Polling-station members frequently leave the cell blank when a "
           "party receives no votes. A blank cell is not an OCR failure but "
           "form semantics, so a post-processing rule maps unread party cells "
           "(and challenged votes) to zero. We report it separately to avoid "
           "crediting vision with domain knowledge."))
E.append(Paragraph("<i>E. Routing born-digital actas</i>", s_h2))
E.append(P("STAE actas are parsed directly from the PDF text layer: each "
           "party name is followed by its typeset count, and summary labels "
           "precede their values. Matching extracted names to official ones "
           "by normalized string equality yields field accuracy without any "
           "image processing."))

E.append(H1("V. E<font size=8>XPERIMENTS</font>"))
E.append(Paragraph("<i>A. Metrics and statistical protocol</i>", s_h2))
E.append(P("<b>Field accuracy</b>: exact match between the read integer and "
           "the official value. <b>CER</b>: character error rate between the "
           "digit strings. Fields within an acta share writer and scan "
           "quality, so the acta is the statistical cluster: confidence "
           "intervals use a <b>clustered bootstrap</b> (10,000 resamples of "
           "whole actas). All evaluation artifacts (per-field errors, "
           "per-acta metrics) ship with the repository."))
E.append(Paragraph("<i>B. Pilot ablation (10 actas, 430 fields)</i>", s_h2))
E.append(P("The pilot — sequential stations of one district, hence biased "
           "but useful for component analysis — quantifies each recognition "
           "improvement (Table I)."))
E.extend(tabla("TABLE I. P<font size=7>ILOT ABLATION ON</font> 10 "
               "<font size=7>ACTAS</font> (430 <font size=7>FIELDS</font>)",
               [["Configuration", "Acc. (%)", "CER"],
                ["v1: raw digit OCR", "43.95", "0.524"],
                ["v2: + ink isolation, borders, sub-boxes", "52.09", "0.419"],
                ["v3: + separator erasure, Otsu, speckle", "52.79", "0.476"],
                ["v4: + empty-cell-is-zero rule", "58.37", "0.420"]]))
E.append(Paragraph("<i>C. National evaluation (76 handwritten actas, 3,268 "
                   "fields)</i>", s_h2))
E.append(P("Table II shows the same system on the random national sample. "
           "Fiducial registration is decisive: without it, framing variation "
           "severely degrades part of the sample (worst acta 14%, CER > 1). Fiducial registration adds "
           "+8.7 points and lifts the worst acta from 14% to 30%; the domain "
           "rule adds +21.6 points — nationally, blank zero-cells are far "
           "more common than in the pilot district."))
E.extend(tabla("TABLE II. N<font size=7>ATIONAL RANDOM SAMPLE</font>, 76 "
               "<font size=7>HANDWRITTEN ACTAS</font> (3,268 "
               "<font size=7>FIELDS</font>)",
               [["Configuration", "Acc. (%)", "CER"],
                ["Fixed template, raw OCR", "26.81", "0.724"],
                ["Fixed template + zero rule", "50.86", "0.482"],
                ["Registered (v5), raw OCR", "38.00", "0.617"],
                ["Registered (v5) + zero rule", "59.58", "0.401"]],
               negrita_ultima=True))
E.append(P("<b>Main result.</b> Field accuracy <b>59.58%, 95% CI "
           "[56.61, 62.48]</b> (±2.94 points); CER <b>0.401, 95% CI "
           "[0.360, 0.444]</b>. Per-acta accuracy averages 59.6% (SD 13.0, "
           "range 30–84%): residual variance stems from handwriting and "
           "digitization quality, no longer from alignment. The pilot figure "
           "(58.4%) happens to be close, but only the national estimate "
           "has a valid margin of error and offers national coverage."))
E.append(P("<b>Born-digital actas.</b> Text-layer parsing of the 24 STAE "
           "actas reaches <b>95.12%</b> (955/1,004 fields); the remaining errors "
           "stem from name matching, not from reading. The contrast with 59.6% quantifies "
           "the value of routing by document type."))
E.append(Paragraph("<i>D. Error analysis</i>", s_h2))
E.append(P("Remaining errors concentrate in: isolated thin digits missed by "
           "the detector stage of the OCR engine; strokes invading the erased "
           "separator bands; shape confusions (8 vs. 18, 7 vs. 9) on wide "
           "handwriting; and multi-box fields. These are recognition errors, "
           "not localization errors — exactly the component that fine-tuning "
           "replaces."))

E.append(H1("VI. C<font size=8>ONCLUSIONS AND</font> F<font size=8>UTURE</font> "
            "W<font size=8>ORK</font>"))
E.append(P("A classical pipeline over real, nationally sampled Peruvian "
           "actas achieves 59.6% field accuracy (95% CI [56.6, 62.5]) on "
           "handwritten documents and 95.1% on born-digital ones, with an "
           "evaluation protocol that needs no manual annotation. Three design "
           "lessons stand out: register templates on the form's fiducial "
           "marks before any fixed-coordinate cropping; separate domain "
           "semantics (blank = 0) from vision performance; and classify the "
           "document type before choosing a processing path. The quantified "
           "ceiling of generic OCR motivates the next steps: fine-tune a "
           "transformer recognizer [4][2] on the free field–value pairs (~43 "
           "per acta, ~43,000 from 1,000 actas), train learned detectors "
           "(YOLOv11, RT-DETR [1]) on labels auto-generated by the registered "
           "template, compare the modular pipeline against unified parsers "
           "[3][5], and explore LLM few-shot labeling as a complementary "
           "annotation source."))

E.append(H1("R<font size=8>EFERENCES</font>"))
for r in [
    "[1] Y. Zhao, W. Lv, S. Xu, J. Wei, G. Wang, Q. Dang, Y. Liu, and "
    "J. Chen, “DETRs beat YOLOs on real-time object detection,” in "
    "<i>Proc. IEEE/CVF CVPR</i>, 2024, pp. 16965–16974.",
    "[2] M. Fujitake, “DTrOCR: Decoder-only transformer for optical "
    "character recognition,” in <i>Proc. IEEE/CVF WACV</i>, 2024, "
    "pp. 8025–8035.",
    "[3] J. Wan, S. Song, W. Yu, Y. Liu, W. Cheng, F. Huang, X. Bai, C. Yao, "
    "and Z. Yang, “OmniParser: A unified framework for text spotting, "
    "key information extraction and table recognition,” in <i>Proc. "
    "IEEE/CVF CVPR</i>, 2024, pp. 15641–15653.",
    "[4] M. Li, T. Lv, J. Chen, L. Cui, Y. Lu, D. Florencio, C. Zhang, "
    "Z. Li, and F. Wei, “TrOCR: Transformer-based optical character "
    "recognition with pre-trained models,” in <i>Proc. AAAI</i>, 2023, "
    "pp. 13094–13102.",
    "[5] G. Kim, T. Hong, M. Yim, J. Nam, J. Park, J. Yim, W. Hwang, S. Yun, "
    "D. Han, and S. Park, “OCR-free document understanding "
    "transformer,” in <i>Proc. ECCV</i>, 2022, pp. 498–517.",
]:
    E.append(Paragraph(r, s_ref))

doc.build(E)
print("PDF generado:", SALIDA)
