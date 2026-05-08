@echo off
setlocal
cd /d "%~dp0"
title Compilar Ufulu Rodec Edition

echo ============================================================
echo   UFULU RODEC EDITION - COMPILADOR
echo ============================================================

where python >nul 2>nul
if errorlevel 1 (echo [ERROR] Python no esta en PATH. & pause & exit /b 1)
if not exist "main.py" (echo [ERROR] No se encuentra main.py & pause & exit /b 1)

echo [1/4] Verificando PyInstaller...
python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 python -m pip install --upgrade pyinstaller

echo [2/4] Verificando dependencias...
for %%P in (PyQt6 librosa numpy scipy mutagen reportlab) do (
    python -c "import %%P" >nul 2>nul
    if errorlevel 1 python -m pip install %%P
)

echo [3/4] Limpiando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "UfuluRodec.spec" del /q "UfuluRodec.spec"

echo [4/4] Compilando (3-5 minutos)...
python -m PyInstaller --onefile --windowed --name "UfuluRodec" ^
    --hidden-import "scipy.signal" ^
    --hidden-import "scipy.signal._peak_finding" ^
    --hidden-import "librosa" --hidden-import "librosa.util" ^
    --hidden-import "soundfile" --hidden-import "audioread" ^
    --hidden-import "mutagen" --hidden-import "mutagen.id3" --hidden-import "mutagen.flac" ^
    --hidden-import "reportlab" --hidden-import "reportlab.pdfgen" ^
    --hidden-import "PyQt6.QtMultimedia" ^
    --collect-data "librosa" --collect-submodules "scipy" ^
    main.py

if errorlevel 1 (echo [ERROR] Compilacion fallida. & pause & exit /b 1)

echo ============================================================
echo   OK -- dist\UfuluRodec.exe listo (150-300 MB es normal)
echo ============================================================
pause
endlocal
