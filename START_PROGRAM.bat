@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
color 0A
cls

echo ═══════════════════════════════════════════════════════════════════════════
echo                   PORNEȘTE PROGRAMUL - WebGSM Import Produse
echo ═══════════════════════════════════════════════════════════════════════════
echo.

:: ──────────────────────────────────────────────────
:: AUTO-UPDATE: Verifică dacă sunt actualizări
:: ──────────────────────────────────────────────────
git --version >nul 2>&1
if not errorlevel 1 (
    if exist ".git" (
        echo ⏳ Verific actualizări...

        :: Fetch fără download (doar verifică)
        git fetch origin >nul 2>&1

        :: Compară local vs remote
        set "LOCAL="
        set "REMOTE="
        for /f %%i in ('git rev-parse HEAD 2^>nul') do set "LOCAL=%%i"
        for /f %%i in ('git rev-parse @{u} 2^>nul') do set "REMOTE=%%i"

        if defined LOCAL if defined REMOTE (
            if not "!LOCAL!"=="!REMOTE!" (
                echo.
                echo ╔═══════════════════════════════════════════════════════════╗
                echo ║  ⚡ ACTUALIZARE DISPONIBILĂ!                            ║
                echo ║  Apasă D pentru DA sau N pentru NU                      ║
                echo ╚═══════════════════════════════════════════════════════════╝
                echo.
                choice /c DN /n /m "Actualizez? [D]a / [N]u: "
                if not errorlevel 2 (
                    echo   → Actualizez...
                    git pull origin main >nul 2>&1 || git pull >nul 2>&1
                    pip install -r requirements.txt --quiet >nul 2>&1
                    echo   ✓ Actualizat!
                ) else (
                    echo   → Continuăm cu versiunea curentă
                )
            ) else (
                echo ✓ Program la zi
            )
        ) else (
            echo ✓ Verificare actualizări: OK
        )
        echo.
    )
)

:: ──────────────────────────────────────────────────
:: Verifică dacă există EXE compilat
:: ──────────────────────────────────────────────────
if exist "dist\ImportProduse.exe" (
    echo ✓ Găsit EXE compilat
    echo.
    echo 🚀 Pornesc ImportProduse.exe...
    echo.
    start "" "dist\ImportProduse.exe"
    exit /b 0
)

:: ──────────────────────────────────────────────────
:: Verifică Python
:: ──────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python NU este instalat și nici EXE-ul nu există!
    echo.
    echo Soluții:
    echo   1. Rulează SETUP_AUTOMAT.bat pentru instalare completă
    echo   2. SAU compilează EXE-ul cu COMPILEAZA_EXE.bat
    echo.
    pause
    exit /b 1
)

echo ✓ Python detectat
echo.

:: ──────────────────────────────────────────────────
:: Verifică .env (configurare)
:: ──────────────────────────────────────────────────
if not exist ".env" (
    echo ╔═══════════════════════════════════════════════════════════╗
    echo ║  ⚠ Fișierul .env nu există!                             ║
    echo ║  Configurează din tab-ul ⚙ Configurare din program.     ║
    echo ╚═══════════════════════════════════════════════════════════╝
    echo.
)

:: ──────────────────────────────────────────────────
:: Pornește programul
:: ──────────────────────────────────────────────────
set PYTHONIOENCODING=utf-8

if exist ".venv\Scripts\python.exe" (
    echo ✓ Mediu virtual .venv găsit
    echo 🚀 Pornesc programul...
    echo.
    ".venv\Scripts\python.exe" import_gui.py
) else (
    echo 🚀 Pornesc programul cu Python global...
    echo.
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

endlocal
