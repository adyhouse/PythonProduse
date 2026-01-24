@echo off
chcp 65001 >nul
color 0A
cls

echo ═══════════════════════════════════════════════════════════════════════════
echo                   PORNEȘTE PROGRAMUL - IMPORT PRODUSE
echo ═══════════════════════════════════════════════════════════════════════════
echo.

:: Verifică dacă există EXE compilat
if exist "dist\ImportProduse.exe" (
    echo ✓ Găsit EXE compilat
    echo.
    echo 🚀 Pornesc ImportProduse.exe...
    echo.
    start "" "dist\ImportProduse.exe"
    exit /b 0
)

:: Verifică Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python NU este instalat și nici EXE-ul nu există!
    echo.
    echo Soluții:
    echo   1. Rulează INSTALARE_PYTHON.bat pentru a instala Python
    echo   2. SAU compilează EXE-ul cu COMPILEAZA_EXE.bat
    echo.
    pause
    exit /b 1
)

echo ✓ Python detectat
echo.

:: Verifică dacă există .venv (mediu virtual)
if exist ".venv\Scripts\python.exe" (
    echo ✓ Mediu virtual .venv găsit
    echo.
    echo 🚀 Pornesc programul cu .venv Python...
    echo.
    
    :: Setează encoding UTF-8
    set PYTHONIOENCODING=utf-8
    
    :: Rulează cu .venv Python
    ".venv\Scripts\python.exe" import_gui.py
) else (
    echo ⚠ Mediu virtual .venv NU găsit
    echo.
    echo 🚀 Pornesc programul cu Python global...
    echo.
    
    :: Setează encoding UTF-8
    set PYTHONIOENCODING=utf-8
    
    :: Rulează cu Python global
    python import_gui.py
)

if errorlevel 1 (
    echo.
    echo ✗ Eroare la pornire!
    echo.
    echo Verifică dacă ai instalat dependințele cu: INSTALEAZA_DEPENDINTE.bat
    echo.
    pause
    exit /b 1
)
