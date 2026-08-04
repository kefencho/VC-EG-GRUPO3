@echo off
REM ============================================================================
REM  EJECUTAR.bat — Corre TODO el pipeline de actas ONPE sin asistente.
REM
REM  Uso:   doble clic  (corre 10 actas)
REM         EJECUTAR.bat 50            (corre 50 actas)
REM         EJECUTAR.bat 10 nopause    (sin pausa final; para scripts/CI)
REM
REM  Etapas: muestreo+descarga -> PDF a PNG -> preproceso -> recorte por
REM  plantilla registrada -> OCR -> evaluacion vs oficial -> estadistica.
REM  Salidas en data\corrida\  (resultados: data\corrida\analisis.json)
REM
REM  Requisitos (ya instalados en esta maquina): Python de C:\ProgramData\
REM  anaconda3 con curl_cffi, pymupdf, opencv, easyocr. Internet para
REM  descargar actas (y modelos de EasyOCR la primera vez).
REM ============================================================================

setlocal
chcp 65001 >nul

REM ---------------------------------------------------------------------------
REM Ir a la carpeta donde esta fichero BAT
REM ---------------------------------------------------------------------------

cd /d "%~dp0"

set "ROOT=%CD%"
set "VENV=%ROOT%\.venv\Scripts\python.exe"

REM ---------------------------------------------------------------------------
REM --- Detectar Python
REM ---------------------------------------------------------------------------
echo Buscando Python...
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo.
        echo ERROR: Python no esta instalado.
        pause
        exit /b 1
    )
)
REM ---------------------------------------------------------------------------
REM Crear entorno virtual
REM ---------------------------------------------------------------------------
if not exist "%ROOT%\.venv" (
    echo Creando entorno virtual...
    %PY% -m venv "%ROOT%\.venv"

    if errorlevel 1 (
        echo ERROR creando el entorno virtual.
        pause
        exit /b 1
    )
)
REM --Activar el entorno
echo Activando el entorno virtual...
set "VENV=.venv\Scripts\python.exe"

REM ---------------------------------------------------------------------------
REM Instalar dependencias
REM ---------------------------------------------------------------------------
echo Instalando requirements.txt...
if not exist "%ROOT%\.venv\.installed" (

    "%VENV%" -m pip install --upgrade pip

    if errorlevel 1 (
        echo ERROR actualizando pip.
        pause
        exit /b 1
    )

    "%VENV%" -m pip install -r "%ROOT%\requirements.txt"

    if errorlevel 1 (
        echo ERROR instalando requirements.txt
        pause
        exit /b 1
    )

    type nul > "%ROOT%\.venv\.installed"
)

REM --- cuantas actas (parametro 1; por defecto 10) --------------------------
set "N=%~1"
if "%N%"=="" set "N=10"

echo.
echo  ============================================================
echo   PIPELINE ACTAS ONPE EG2026  -  %N% actas (muestreo nacional)
echo  ============================================================
echo.

::echo [1/7] Muestreo aleatorio nacional + descarga de PDFs y votos oficiales...
::pushd src\scraper
::"%VENV%" "%ROOT%\src\scraper\muestreo_nacional.py" --n %N% --seed 2026 --out "%ROOT%\data\corrida"
::if errorlevel 1 goto :error
::popd

echo [2/7] Convirtiendo PDF a PNG (300 DPI)...
"%VENV%" "%ROOT%\src\scraper\pdf_to_images.py" --in "%ROOT%\data\corrida\raw_pdf" --out "%ROOT%\data\corrida\raw_img" --dpi 300
if errorlevel 1 goto :error

echo [3/7] Preprocesando (deskew + CLAHE + denoise)...
"%VENV%" "%ROOT%\src\preprocessing\preprocess.py" --in "%ROOT%\data\corrida\raw_img" --out "%ROOT%\data\corrida\processed"
if errorlevel 1 goto :error

echo [4/7] Recortando 46 regiones por plantilla registrada (fiduciales)...
"%VENV%" "%ROOT%\src\detection\regiones_plantilla.py" --in "%ROOT%\data\corrida\processed" --out "%ROOT%\data\corrida\crops"
if errorlevel 1 goto :error

REM las actas electronicas (STAE, 2 paginas -> carpetas _p0/_p1) no van al OCR
for /d %%D in ("%ROOT%\data\corrida\crops\*_p0") do rd /s /q "%%D"
for /d %%D in ("%ROOT%\data\corrida\crops\*_p1") do rd /s /q "%%D"

echo [5/7] Leyendo con OCR (aprox. 1 min por acta en CPU; paciencia)...
"%VENV%" "%ROOT%\src\pipeline\piloto_10_actas.py" --modo limpio --crops "%ROOT%\data\corrida\crops" --gt "%ROOT%\data\corrida\ground_truth" --out "%ROOT%\data\corrida\salida"
if errorlevel 1 goto :error

echo [6/7] Evaluando contra los votos oficiales (regla celda-vacia = 0)...
"%VENV%" "%ROOT%\src\pipeline\evaluar_salidas.py" --salidas "%ROOT%\data\corrida\salida" --gt "%ROOT%\data\corrida\ground_truth" --regla-cero --out "%ROOT%\data\corrida\evaluacion.json"
if errorlevel 1 goto :error

echo [7/7] Estadistica: exactitud con IC 95%% (bootstrap por acta)...
"%VENV%" "%ROOT%\src\pipeline\analisis_estadistico.py" --eval "%ROOT%\data\corrida\evaluacion.json" --muestra "%ROOT%\data\corrida\muestra.json" --out "%ROOT%\data\corrida\analisis.json"
if errorlevel 1 goto :error

echo.
echo  ============================================================
echo   LISTO. Resultados en data\corrida\ :
echo     - analisis.json     (exactitud + IC 95%%)
echo     - evaluacion.json   (detalle por acta y por campo)
echo     - salida\*.json     (lectura estructurada de cada acta)
echo  ============================================================
if /i not "%~2"=="nopause" pause
exit /b 0

:error
popd 2>nul
echo.
echo  *** ERROR en la etapa anterior. Revisa el mensaje de arriba. ***
echo  Pistas: internet activo? EasyOCR descarga modelos la 1ra vez.
if /i not "%~2"=="nopause" pause
exit /b 1
