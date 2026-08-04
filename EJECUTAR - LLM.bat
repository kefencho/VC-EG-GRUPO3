@echo off
REM ============================================================================
REM  EJECUTAR - LLM.bat
REM
REM  Ejecuta el reconocimiento OCR mediante Gemini.
REM
REM  Requisitos:
REM    - Python instalado
REM    - requirements.txt instalado
REM    - archivo .env con GEMINI_API_KEY en la raiz del proyecto
REM
REM  Uso:
REM      doble clic
REM      EJECUTAR - LLM.bat 15
REM      EJECUTAR - LLM.bat 30
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
set "VENV=%ROOT%\.venv\Scripts\python.exe"

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
if "%N%"=="" set "N=15"

echo.
echo  ============================================================
echo   OCR CON GEMINI - ACTAS ONPE 2026
echo  ============================================================
echo.
echo Numero de actas : %N%
echo Modelo          : Gemini
echo Shots           : 2
echo.

REM ---------------------------------------------------------------------------
REM Verificar archivo .env
REM ---------------------------------------------------------------------------

if not exist "%ROOT%\.env" (
    echo.
    echo ERROR: No existe el archivo .env
    echo.
    echo Debe crear:
    echo     %ROOT%\.env
    echo.
    echo Con el contenido:
    echo     GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM Ejecutar OCR con LLM
REM ---------------------------------------------------------------------------

echo [1/1] Ejecutando OCR mediante Gemini...
"%VENV%" "%ROOT%\src\recognition\llm_ocr.py" --n %N% --shots 2 --procesadas "%ROOT%\data\muestra\processed" --gt "%ROOT%\data\muestra\ground_truth" --tipos "%ROOT%\data\muestra\tipos.json" --out "%ROOT%\data\muestra\salida_llm"
if errorlevel 1 goto :error

echo.
echo ============================================================
echo PROCESO FINALIZADO CORRECTAMENTE
echo ============================================================
echo.
echo Resultados generados en:
echo.
echo     %ROOT%\data\muestra\salida_llm
echo.

if /i not "%~2"=="nopause" pause
exit /b 0

:error
echo.
echo ************************************************************
echo ERROR EN LA EJECUCION DEL OCR CON GEMINI
echo ************************************************************
echo Revise el mensaje mostrado anteriormente.
echo.
if /i not "%~2"=="nopause" pause
exit /b 1
