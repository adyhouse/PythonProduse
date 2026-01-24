@echo off
chcp 65001 >nul
color 0A
cls

echo ═══════════════════════════════════════════════════════════════════════════
echo              INSTALARE DEPENDINȚE PYTHON - IMPORT PRODUSE
echo ═══════════════════════════════════════════════════════════════════════════
echo.

:: Verifică Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python NU este instalat!
    echo.
    echo Rulează mai întâi: INSTALARE_PYTHON.bat
    echo.
    pause
    exit /b 1
)

echo ✓ Python detectat:
python --version
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Instalăm pachetele necesare...
echo.

:: Upgrade pip
echo [1/7] Actualizăm pip...
python -m pip install --upgrade pip

:: Instalează dependințe
echo.
echo [2/7] Instalăm requests (pentru API și download)...
python -m pip install requests

echo.
echo [3/7] Instalăm beautifulsoup4 (pentru web scraping)...
python -m pip install beautifulsoup4

echo.
echo [4/7] Instalăm woocommerce (pentru API WooCommerce)...
python -m pip install woocommerce

echo.
echo [5/7] Instalăm Pillow (pentru procesare imagini)...
python -m pip install Pillow

echo.
echo [6/7] Instalăm python-dotenv (pentru configurare)...
python -m pip install python-dotenv

echo.
echo [7/8] Instalăm deep-translator (pentru traduceri automate)...
python -m pip install deep-translator

echo.
echo [8/8] Instalăm PyInstaller (pentru creare EXE)...
python -m pip install pyinstaller

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo ✓ Toate dependințele au fost instalate cu succes!
echo.
echo Următorul pas: Rulează IMPORT_PRODUSE.bat (versiunea Python cu GUI)
echo.
pause
